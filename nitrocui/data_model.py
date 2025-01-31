"""
NITROC data model

collects data from various sources and stores them in a in-memory
"database".

To enable ODB-II speed polling add the following to the nitroc configuration
file /etc/nitrocui.conf

[OBD2]
Port = CAN port to use, e.g. can0
Speed = Bitrate to use. Either 250000 or 500000
"""

import configparser
import logging
import platform
import threading
import time

from .led import LED_BiColor
from .mm import MM
from .sysinfo_thermal import SysInfoThermal
from .sysinfo_tc import SysInfoTC
from .sysinfo_sensors import SysInfoSensors
from .sysinfo_power import SysInfoPower
from .crosec_sensors import CrosEcSensors
from .vnstat import VnStat


CONF_FILE = '/etc/nitrocui.conf'


logger = logging.getLogger('nitroc-ui')


class Model(object):
    # Singleton accessor
    instance = None

    def __init__(self):
        super().__init__()

        assert Model.instance is None
        Model.instance = self

        self.linux_release = platform.release()

        self.worker = ModelWorker(self)
        self.lock = threading.Lock()
        self.data = dict()
        self.data['watermark'] = dict()

        self.led_ind = LED_BiColor('/sys/class/leds/ind')
        self.led_stat = LED_BiColor('/sys/class/leds/status')
        self.cnt = 0

        self.config = configparser.ConfigParser()
        try:
            self.config.read(CONF_FILE)
            self.config.wwan_interface = self.config.get('WWAN', 'Interface')
            self.config.wlan_interface = self.config.get('WLAN', 'Interface')
        except configparser.Error as e:
            self.config.wwan_interface = 'wwan0'
            self.config.wlan_interface = 'wlan0'
            logger.warning(f'ERROR: Cannot get config from {CONF_FILE}')
            logger.info(e)

    def setup(self):
        self.led_stat.green()
        self.led_ind.green()

        self.worker.setup()

    def get_all(self):
        with self.lock:
            return self.data

    def get(self, origin):
        with self.lock:
            if origin in self.data:
                return self.data[origin]

    def publish(self, origin, value):
        """
        Report event (with data) to data model

        Safe to be called from any thread
        """
        # logger.debug(f'get data from {origin}')
        # logger.debug(f'values {value}')
        with self.lock:
            self.data[origin] = value

            if origin == 'things':
                if value['state'] == 'sending':
                    self.led_ind.yellow()
                else:
                    self.led_ind.green()
            elif origin == 'modem':
                if 'bearer-uptime' in value:
                    self._watermark('bearer-uptime', value['bearer-uptime'])

    def remove(self, origin):
        with self.lock:
            self.data.pop(origin, None)

    def _watermark(self, topic, value):
        if topic not in self.data['watermark']:
            logger.info(f'creating watermark topic {topic}')
            self.data['watermark'][topic] = None

        curr = self.data['watermark'][topic]
        logger.debug(f'checking watermark {topic}, current = {curr}, new = {value}')

        if curr is None or value > curr:
            self.data['watermark'][topic] = value
            logger.debug(f'new watermark for {topic} = {value}')


class ModelWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.modem_setup_done = False

    def setup(self):
        self.lock = threading.Lock()
        self.daemon = True
        self.name = 'model-worker'

        self.si = SysInfoSensors()
        self.crosi = CrosEcSensors()
        self.sit = SysInfoThermal()
        self.sip = SysInfoPower()
        self.tc = SysInfoTC()

        self._traffic_mon_setup()

        self.start()

    def run(self):
        cnt = 0
        while True:
            self._sysinfo()

            if cnt == 0 or cnt % 4 == 2:
                self._network()

            # if cnt == 0 or cnt % 4 == 3:
            #     self._100base_t1()

            if cnt == 0 or cnt % 4 == 2:
                self._modem()

            if cnt == 0 or cnt % 120 == 15:
                self._disc()

            # if self.model.obd2_port:
            #     # if cnt == 0 or cnt % 2 == 1:
            #     self._obd2_poll()

            if cnt == 0 or cnt % 20 == 12:
                self._traffic()

            cnt += 1
            time.sleep(1.0)

    def _sysinfo(self):
        si = self.si
        crosi = self.crosi
        sit = self.sit
        sip = self.sip
        tc = self.tc

        # Give each sensor subsystem a chance to efficiently get all required data at once
        si.poll()
        crosi.poll()
        sit.poll()
        sip.poll()
        tc.poll()

        ver = dict()
        ver['serial'] = si.serial()
        ver['sys'] = si.version()
        ver['bl'] = si.bootloader_version()
        ver['hw'] = si.hw_version()
        self.model.publish('sys-version', ver)

        start = dict()
        start['reason'] = si.start_reason()
        self.model.publish('sys-boot', start)

        dt = dict()
        dt['date'] = si.date()
        dt['uptime'] = si.uptime()
        self.model.publish('sys-datetime', dt)

        info = dict()
        info['mem'] = si.meminfo()
        info['load'] = si.load()
        info['cpu1_freq'] = si.cpufreq(0)
        info['cpu2_freq'] = si.cpufreq(1)
        info['cpu3_freq'] = si.cpufreq(2)
        info['cpu4_freq'] = si.cpufreq(3)

        info['temp_mb'] = si.temperature_mb1_pcb()
        info['temp_mb2'] = si.temperature_mb2_pcb()
        info['temp_eth'] = si.temperature_eth_pcb()
        info['temp_nmcf1'] = si.temperature_nmcf1_pcb()
        info['temp_nmcf2'] = si.temperature_nmcf2_pcb()
        info['temp_nmcf3'] = si.temperature_nmcf3_pcb()
        info['temp_nmcf4'] = si.temperature_nmcf4_pcb()
        info['temp_phy1'] = si.temperature_phy1()
        info['temp_phy2'] = si.temperature_phy2()
        info['temp_phy3'] = si.temperature_phy3()
        info['temp_eth_switch'] = si.temperature_eth_switch()

        info['temp_ap'] = sit.temp_ap()
        info['temp_cp0'] = sit.temp_cp0()
        info['temp_cp2'] = sit.temp_cp2()
        # print(info['temp_ap'], info['temp_cp0'], info['temp_cp2'])

        info['temp_nvm_ssd'] = si.temperature_nvm_ssd()
        info['temp_wifi_wle3000'] = si.temperature_wifi_wle3000()

        # TODO: for loop
        info["temp_tc1"] = tc.temp_tc(0)
        info["temp_tc2"] = tc.temp_tc(1)
        info["temp_tc3"] = tc.temp_tc(2)
        info["temp_tc4"] = tc.temp_tc(3)
        info["temp_tc5"] = tc.temp_tc(4)
        info["temp_tc6"] = tc.temp_tc(5)
        info["temp_tc7"] = tc.temp_tc(6)
        # info["temp_tc8"] = tc.temp_tc(7)

        info['pwr_mb'] = sip.pwr_mb()
        info['pwr_eth'] = sip.pwr_eth()
        info['pwr_nmcf1'] = sip.pwr_nmcf1()
        info['pwr_nmcf2'] = sip.pwr_nmcf2()
        info['pwr_nmcf3'] = sip.pwr_nmcf3()
        info['pwr_nmcf4'] = sip.pwr_nmcf4()

        info['v_in'] = crosi.input_voltage()
        info['v_rtc'] = crosi.rtc_voltage()

        self.model.publish('sys-misc', info)

    def _disc(self):
        si = self.si

        disc = dict()
        disc['wear'] = si.emmc_wear()
        disc['part_sysroot'] = si.part_size('/')
        # disc['part_data'] = si.part_size('/data')
        self.model.publish('sys-disc', disc)

    def _network(self):
        si = self.si
        config = self.model.config

        info_wwan = dict()
        info_wwan['bytes'] = si.ifinfo(config.wwan_interface) #  'wwan0')
        self.model.publish('net-wwan0', info_wwan)

        info_wlan = dict()
        info_wlan['bytes'] = si.ifinfo(config.wlan_interface) # 'wlan0')
        self.model.publish('net-wlan0', info_wlan)

    def _modem_setup(self, m):
        logger.info("enabling signal query")
        if m:
            m.setup_signal_query()
            self.modem_setup_done = True
        else:
            logger.info("modem not yet ready")

    def _modem(self):
        info = dict()
        m = MM.modem()
        if m:
            if not self.modem_setup_done:
                self._modem_setup(m)

            info['modem-id'] = str(m.id)
            m_info = m.get_info()

            info['vendor'] = m.vendor(m_info)
            info['model'] = m.model(m_info)
            info['revision'] = m.revision(m_info)

            state = m.state(m_info)
            access_tech = m.access_tech(m_info)
            access_tech2 = m.access_tech2(m_info)

            info['state'] = state
            info['access-tech'] = access_tech
            if access_tech2:    # Optional 2nd access tech, i.e. lte and 5gnr
                info['access-tech2'] = access_tech2

            loc_info = m.location()
            if loc_info['mcc']:
                info['location'] = loc_info

            sq = m.signal_quality(m_info)
            info['signal-quality'] = sq

            # Get access tech from signal quality command as regular RAT
            # information from ModemManager is not reliable
            sig_info = m.signal_get()

            # sig_rat = m.access_tech(sig_info)
            # sig_rat2 = m.access_tech2(sig_info)
            # print(sig_rat, sig_rat2)

            # FN990 reports LTE and 5G as 2nd technology
            if access_tech == '5gnr' or access_tech2 == '5gnr':
                sig = m.signal_5g(sig_info)
                info['signal-5g'] = sig

            if access_tech == 'lte':
                sig = m.signal_lte(sig_info)
                info['signal-lte'] = sig

                # Seldomly the signal fields are not defined, handle gracefully
                # if sig['rsrq'] and sig['rsrp']:
                #     # Compute an alternate signal quality indicator to ModemManager
                #     lte_q = SignalQuality_LTE(sig['rsrq'], sig['rsrp'])
                #     qual = lte_q.quality() * 100.0
                #     info['signal-quality2'] = round(qual)

            if access_tech == 'umts':
                sig = m.signal_umts(sig_info)
                info['signal-umts'] = sig

            b = m.bearer(m_info)
            if b:
                b_info = b.get_info()

                info['bearer-id'] = str(b.id)
                ut = b.uptime(b_info)
                if ut:
                    info['bearer-uptime'] = ut
                ip = b.ip(b_info)
                if ip:
                    info['bearer-ip'] = ip

            s = m.sim(m_info)
            if s:
                info['sim-id'] = str(s.id)

                s_info = s.get_info()
                imsi = s.imsi(s_info)
                info['sim-imsi'] = imsi
                iccid = s.iccid(s_info)
                info['sim-iccid'] = iccid
        else:
            self.modem_setup_done = False

        self.model.publish('modem', info)



    def _traffic_mon_setup(self):
        logger.warning('setting up traffic monitoring')

        if VnStat.probe():
            self._vnstat = VnStat('wwan0')
            # print(f'version is {VnStat.version}')
        else:
            self._vnstat = None
            logger.info('traffic monitoring disabled')

    def _traffic(self):
        if self._vnstat:
            info = self._vnstat.get()
            if info:
                self.model.publish('traffic-wwan0', info)
