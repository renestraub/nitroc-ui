import logging
import re
import threading
import time

# TODO: Factor out NEO-M8 Code to dedicated 'driver' class
from ubxlib.server import GnssUBlox
from ubxlib.ubx_cfg_cfg import UbxCfgCfgAction
from ubxlib.ubx_cfg_esfalg import UbxCfgEsfAlg, UbxCfgEsfAlgPoll
from ubxlib.ubx_cfg_esfla import UbxCfgEsflaPoll, UbxCfgEsflaSet
from ubxlib.ubx_cfg_nav5 import UbxCfgNav5Poll
from ubxlib.ubx_cfg_nmea import UbxCfgNmeaPoll
from ubxlib.ubx_cfg_prt import UbxCfgPrtPoll
from ubxlib.ubx_cfg_rst import UbxCfgRstAction
from ubxlib.ubx_esf_alg import UbxEsfAlgPoll
from ubxlib.ubx_esf_status import UbxEsfStatusPoll
from ubxlib.ubx_mon_ver import UbxMonVerPoll
from ubxlib.ubx_upd_sos import UbxUpdSosAction
from nitrocui.gpsd import Gpsd

logger = logging.getLogger('nitroc-ui')


class Gnss(threading.Thread):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert Gnss.instance is None
        Gnss.instance = self

        self.model = model
        self.ubx = None
        self.lock = threading.Lock()

        # Static values, read once in setup()
        self.__msg_mon_ver = None
        self.__msg_cfg_port = None
        self.__msg_cfg_nmea = None

        # Config values, can be cached until changed by model itself
        self._clear_cached_values()

        # Live values, can be cached on page reload, see invalidate()
        self.__msg_esf_alg = None

        self.esf_read_errors = 0

        self.state = 'init'

    def setup(self):
        # Just start worker thread. As soon as we are connected to gpsd
        # actions starts from there
        self.daemon = True
        self.name = 'gnss-status'
        self.start()

    def invalidate(self):
        with self.lock:
            self.__msg_cfg_esfalg = None
            self.__msg_esf_alg = None

    def gpsd_connected(self):
        with self.lock:
            return self.state == 'connected' and self.ubx

    def version(self):
        """
        extension_0: ROM BASE 3.01 (107888)
        extension_1: FWVER=ADR 4.21
        extension_2: PROTVER=19.20
        extension_3: MOD=NEO-M8L-0
        extension_4: FIS=0xEF4015 (100111)
        extension_5: GPS;GLO;GAL;BDS
        extension_6: SBAS;IMES;QZSS
        """
        ver = self._mon_ver()
        if ver:
            fw = ver.f.extension_1.split('=')[1]
            proto = ver.f.extension_2.split('=')[1]

            data = {
                'swVersion': Gnss.sanitize(ver.f.swVersion),
                'hwVersion': Gnss.sanitize(ver.f.hwVersion),
                'fwVersion': Gnss.sanitize(fw),
                'protocol': Gnss.sanitize(proto)
            }
        else:
            data = {
                'swVersion': 'n/a',
                'hwVersion': 'n/a',
                'fwVersion': 'n/a',
                'protocol': 'n/a'
            }
        return data

    @staticmethod
    def sanitize(string_with_zeroes):
        return string_with_zeroes.rstrip('\0x00')

    def uart_settings(self):
        cfg = self._cfg_port()
        if cfg:
            mode_str = str(cfg.get('mode')).split(': ')[1]
            data = {
                'bitrate': int(cfg.f.baudRate),
                'mode': mode_str
            }
        else:
            data = {
                'bitrate': 0,
                'mode': 'n/a'
            }
        return data

    def nmea_protocol(self):
        res = self._cfg_nmea()
        if res:
            ver_in_hex = res.f.nmeaVersion
            ver = int(ver_in_hex / 16)
            rev = int(ver_in_hex % 16)
        else:
            ver = 0
            rev = 0

        return f'{ver}.{rev}'

    def cold_start(self):
        logger.debug('executing GNSS cold start')

        # This request is neither ACK'ed, nor a response is available
        with self.lock:
            msg = UbxCfgRstAction()
            msg.cold_start()
            self.ubx.fire_and_forget(msg)

        self._clear_cached_values()

        return 'Success'

    """
    Config Save / Reset
    """
    def reset_config(self):
        logger.debug('resetting GNSS config')

        with self.lock:
            msg = UbxCfgCfgAction()
            msg.reset(UbxCfgCfgAction.MASK_NavConf)
            self.ubx.set(msg)

        self._clear_cached_values()

        return 'Success'

    """
    SOS - Save on Shutdown
    TODO: Remove?
    """
    def save_state(self):
        logger.debug('saving GNSS state (save on shutdown)')

        logger.debug('stopping receiver')
        with self.lock:
            msg = UbxCfgRstAction()
            msg.stop()

            # This request is neither ACK'ed, nor a response is available
            self.ubx.send(msg)
            self.ubx.fire_and_forget(msg)

        time.sleep(0.5)

        logger.debug('saving')
        with self.lock:
            msg = UbxUpdSosAction()
            msg.backup()
            self.ubx.set(msg)

        logger.debug('restarting')
        with self.lock:
            msg = UbxCfgRstAction()
            msg.start()
            self.ubx.fire_and_forget(msg)      # Will not be ACK'ed

        return 'Success'

    def clear_state(self):
        logger.debug('clearing GNSS state (save on shutdown)')

        with self.lock:
            msg = UbxUpdSosAction()
            msg.clear()
            self.ubx.fire_and_forget(msg)

        return 'Success'

    """
    Get/set dynamic model
    """
    def dynamic_model(self):
        res = self._cfg_nav5()
        if res:
            return res.f.dynModel
        else:
            return -1

    """
    IMU Auto Alignment Configuration
    """
    def auto_align(self):
        res = self._cfg_esfalg()
        if res:
            return bool(res.f.bitfield & UbxCfgEsfAlg.BITFIELD_doAutoMntAlg)
        else:
            return -1

    def imu_cfg_angles(self):
        res = self._cfg_esfalg()
        if res:
            data = {
                'roll': res.f.roll / 100.0,
                'pitch': res.f.pitch / 100.0,
                'yaw': res.f.yaw / 100.0
            }
        else:
            logger.warning('cannot get IMU angles')
            data = {
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.0
            }
        return data

    """
    IMU Auto Alignment State
    """
    def auto_align_state(self):
        if not self.__msg_esf_alg:
            self.__msg_esf_alg = self._esf_alg()

        if self.__msg_esf_alg:
            res = str(self.__msg_esf_alg.get('flags'))
            res = res[len('flags: '):]
        else:
            logger.warning('cannot get auto alignment state')
            res = '<error>'
        return res

    def auto_align_angles(self):
        if not self.__msg_esf_alg:
            self.__msg_esf_alg = self._esf_alg()

        if self.__msg_esf_alg:
            roll = self.__msg_esf_alg.f.roll / 100.0
            pitch = self.__msg_esf_alg.f.pitch / 100.0
            yaw = self.__msg_esf_alg.f.yaw / 100.0
        else:
            logger.warning('cannot get auto alignment angles')
            roll, pitch, yaw = 0.0, 0.0, 0.0
        return (roll, pitch, yaw)

    """
    Lever Arm Configuration
    """
    def vrp_ant(self):
        res = self._cfg_vrp_ant()
        if res:
            data = res
        else:
            # TODO: Use error values like -99.99 ?
            logger.warning('cannot get VRP-ANT lever arm')
            data = {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0
            }
        return data

    def vrp_imu(self):
        res = self._cfg_vrp_imu()
        if res:
            data = res
        else:
            # TODO: Use error values like -99.99 ?
            logger.warning('cannot get VRP-IMU lever arm')
            data = {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0
            }
        return data

    """
    Fusion State
    """
    def esf_status(self):
        res = self._esf_status()
        if res:
            stat0_str = str(res.get('fusionMode'))
            stat1_str = str(res.get('initStatus1'))
            stat2_str = str(res.get('initStatus2'))
            data = {
                'fusion': Gnss.__extract(stat0_str, 'fusionMode'),
                'ins': Gnss.__extract(stat1_str, 'ins'),
                'imu': Gnss.__extract(stat2_str, 'imu'),
                'imu-align': Gnss.__extract(stat1_str, 'mntAlg'),
            }
            self.esf_read_errors = 0
        else:
            logger.warning('reading fusion state failed')
            self.esf_read_errors += 1
            data = {
                'fusion': '-',
                'ins': '-',
                'imu': '-',
                'imu-align': '-',
            }
        return data

    #
    # Worker thread
    #
    def run(self):
        self.state = 'init'

        cnt = 0
        while True:
            logger.debug(f'gnss status thread: {self.state}')

            if self.state == 'init':
                self._state_init()
            elif self.state == 'setup':
                self._state_setup()
            elif self.state == 'connected':
                if cnt % 10 == 3:
                    self._state_connected()
            elif self.state == 'timeout':
                self._state_timeout()

            cnt += 1
            time.sleep(1.0)

    def _state_init(self):
        logger.debug('trying to connect to gpsd')

        gps = Gpsd()

        res = gps.setup()
        if res:
            logger.info('gpsd connected')
            # gpsd is around, socket exists
            # wait until first data is seen
            res = gps.next(timeout=10)
            if res:
                logger.info('gps connected')
                self.state = 'setup'
            else:
                # No data incoming
                logger.warning('no data from gpsd, is it running?')
                time.sleep(3.0)
        else:
            logger.warning('cannot connect to gpsd, is it running?')
            time.sleep(3.0)

        gps.cleanup()
        gps = None

    def _state_setup(self):
        # Trying to connect to ubxlib
        logger.debug('setting up gpsd library')

        # TODO: Should ubx object be member of thread?
        self.ubx = GnssUBlox()
        self.ubx.setup()
        # TODO: What about error handling here?

        # Read constant information, never reloaded
        self._mon_ver()
        self._cfg_port()
        self._cfg_nmea()

        versions = self.version()
        logger.info(f'versions: {versions}')
        self.model.publish('gnss', versions)

        self.state = 'connected'

    def _state_connected(self):
        assert self.ubx

        logger.debug('checking gps fusion state')
        info = dict()
        esf_status = self.esf_status()
        info['esf-status'] = esf_status
        self.model.publish('gnss-state', info)

        if self.esf_read_errors > 0:
            logger.warning(f'gpsd access errors detected ({self.esf_read_errors})')
            if self.esf_read_errors >= 3:
                logger.warning('gpsd connection might be broken')
                self.state = 'timeout'

    def _state_timeout(self):
        logger.warning('connection to gpsd lost')
        self.ubx.cleanup()
        self.ubx = None

        self.state = 'init'

    """
    Modem access
    Try to cache accesses as much as possible
    """
    def _mon_ver(self):
        if not self.__msg_mon_ver:
            logger.debug('rereading __msg_mon_ver')
            with self.lock:
                self.__msg_mon_ver = self.ubx.poll(UbxMonVerPoll())

        return self.__msg_mon_ver

    def _cfg_port(self):
        if not self.__msg_cfg_port:
            logger.debug('rereading __msg_cfg_port')
            with self.lock:
                m = UbxCfgPrtPoll()
                m.f.PortId = UbxCfgPrtPoll.PORTID_Uart
                self.__msg_cfg_port = self.ubx.poll(m)

        return self.__msg_cfg_port

    def _cfg_nav5(self, force=False):
        if force or not self.__msg_cfg_nav5:
            logger.debug('rereading __msg_cfg_nav5')
            with self.lock:
                self.__msg_cfg_nav5 = self.ubx.poll(UbxCfgNav5Poll())

        return self.__msg_cfg_nav5

    def _cfg_nmea(self):
        if not self.__msg_cfg_nmea:
            logger.debug('rereading __msg_cfg_nmea')
            with self.lock:
                self.__msg_cfg_nmea = self.ubx.poll(UbxCfgNmeaPoll())

        return self.__msg_cfg_nmea

    def _cfg_esfalg(self, force=False):
        if force or not self.__msg_cfg_esfalg:
            logger.debug('rereading __msg_cfg_esfalg')
            with self.lock:
                self.__msg_cfg_esfalg = self.ubx.poll(UbxCfgEsfAlgPoll())

        return self.__msg_cfg_esfalg

    def _cfg_vrp_imu(self, force=False):
        if force or not self.__msg_cfg_esfla:
            logger.info('rereading __msg_cfg_esfla')
            with self.lock:
                self.__msg_cfg_esfla = self.ubx.poll(UbxCfgEsflaPoll())

        # In case of gpsd access errors reponse object does not exist
        if self.__msg_cfg_esfla:
            lever_IMU = self.__msg_cfg_esfla.lever_arm(UbxCfgEsflaSet.TYPE_VRP_IMU)
            return lever_IMU

    def _cfg_vrp_ant(self, force=False):
        if force or not self.__msg_cfg_esfla:
            logger.info('rereading __msg_cfg_esfla')
            with self.lock:
                self.__msg_cfg_esfla = self.ubx.poll(UbxCfgEsflaPoll())

        # In case of gpsd access errors reponse object does not exist
        if self.__msg_cfg_esfla:
            lever_antenna = self.__msg_cfg_esfla.lever_arm(UbxCfgEsflaSet.TYPE_VRP_Antenna)
            return lever_antenna

    def _esf_alg(self):
        # TODO: Cache result, only reload if required (invalidate)
        with self.lock:
            msg = UbxEsfAlgPoll()
            res = self.ubx.poll(msg)
            return res

    def _esf_status(self):
        with self.lock:
            res = self.ubx.poll(UbxEsfStatusPoll())
            return res

    def _clear_cached_values(self):
        self.__msg_cfg_nav5 = None
        self.__msg_cfg_esfalg = None
        self.__msg_cfg_esfla = None

    @staticmethod
    def __extract(text, token):
        p = re.compile(token + r': ([a-z]*)')
        res = p.findall(text)
        if res:
            return res[0]
        else:
            return '-'
