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
from typing import TypeVar, cast

from .led import LED_RGB
from .mm import MM
from .sysinfo_thermal import SysInfoThermal
from .sysinfo_tc import SysInfoTC
from .sysinfo_sensors import SysInfoSensors
from .sysinfo_power import SysInfoPower
from .crosec_sensors import CrosEcSensors
from .vnstat import VnStat
from .tools import dbus_network_check


CONF_FILE = '/etc/nitrocui.conf'


logger = logging.getLogger('nitroc-ui')


T = TypeVar("T")

class ModelData():
    def __init__(self, data):
        super().__init__()
        self._data = data

    def __contains__(self, key):
        return key in self._data  # Enables `key in obj`

    def __getitem__(self, key):
        return self._data[key]  # Raises KeyError if key is missing

    def get(self, default: T, *keys) -> T:
        """
        Safely retrieve a value from a nested dictionary.

        :param default: The default value if keys are not found.
        :param keys: The sequence of keys to access the value.
        :return: The value if found, otherwise the default.
        """
        try:
            res = self._navigate_dict(*keys)
            return cast(T, res)
        except KeyError as e:
            logger.debug(f'cannot get {e}')
            return default

    def exists(self, *keys) -> bool:
        """
        Check if a nested key path exists in the dictionary.

        :param keys: The sequence of keys to check.
        :return: True if the path exists, otherwise False.
        """
        try:
            self._navigate_dict(*keys)
            return True
        except KeyError:
            return False

    def _navigate_dict(self, *keys) -> dict:
        """
        Navigate through a nested dictionary using keys.

        :param dct: The dictionary to navigate.
        :param keys: The sequence of keys to access the nested value.
        :return: The final value if all keys exist, else raises KeyError.
        """
        dct = self._data
        for key in keys:
            dct = dct[key]  # May raise KeyError
        return dct


class Model(object):
    # Singleton accessor
    instance = None

    DEFAULTS = {
        'WWAN': {
            'IMEI': '.*',
            'Interface': 'wwan0'
        },
        'WLAN': {
            'Interface': 'wlan0'
        }
    }

    def __init__(self):
        super().__init__()

        assert Model.instance is None
        Model.instance = self

        self.linux_release = platform.release()

        self.worker = ModelWorker(self)
        self.lock = threading.Lock()
        self.data = dict()
        self.data['watermark'] = dict()

        self.led_color = "green"
        self.system_led = LED_RGB()
        self.cnt = 0

        self.config = configparser.ConfigParser()
        try:
            self.config.read(CONF_FILE)
            logger.info(f'successfully loaded config from {CONF_FILE}')
        except configparser.Error as e:
            # Fallback to defaults if the config file cannot be read
            logger.warning(f'cannot get config from {CONF_FILE}, using defaults')
            logger.info(e)

        # Explicitly check for IMEI in the WWAN section
        self.wwan_imei = self.config.get('WWAN', 'IMEI', fallback=self.DEFAULTS['WWAN']['IMEI'])
        self.wwan_interface = self.config.get('WWAN', 'Interface', fallback=self.DEFAULTS['WWAN']['Interface'])
        self.wlan_interface = self.config.get('WLAN', 'Interface', fallback=self.DEFAULTS['WLAN']['Interface'])

    def setup(self):
        self.system_led.color(self.led_color)

        self.worker.setup()

    def get_all(self) -> ModelData:
        with self.lock:
            return ModelData(self.data)

    def get_section(self, origin) -> (ModelData | None):
        with self.lock:
            if origin in self.data:
                return ModelData(self.data[origin])

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
                    # Set LED to yellow, while transmitting
                    self.system_led.yellow()
                else:
                    # Revert back to user defined color
                    self.system_led.color(self.led_color)
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
        # logger.debug(f'checking watermark {topic}, current = {curr}, new = {value}')

        if curr is None or value > curr:
            self.data['watermark'][topic] = value
            logger.debug(f'new watermark for {topic} = {value}')

    def indicator(self, color: str) -> None:
        self.led_color = color
        self.system_led.color(self.led_color)


class ModelWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.modem_setup_done = False

    def setup(self):
        self.lock = threading.Lock()
        self.daemon = True
        self.name = 'model-worker'

        # Check presence of required tools
        if not SysInfoSensors.sensors_present():
            logger.warn('System sensors not present, is the "sensors" tool available?')
        if not CrosEcSensors.sensors_present():
            logger.warn('EC sensors not present, is the "ectool" available?')

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
        ver['bl'] = crosi.bootloader_version()
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
        # print(info['temp_tc1'], info['temp_tc2'], info['temp_tc3'], info['temp_tc3'])
        # print(info['temp_tc5'], info['temp_tc6'], info['temp_tc7'])

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

        info_net = dict()
        conn_state = dbus_network_check()
        info_net['inet-conn'] = conn_state
        self.model.publish('network', info_net)

        info_wwan = dict()
        info_wwan['bytes'] = si.ifinfo(self.model.wwan_interface)
        self.model.publish('net-wwan0', info_wwan)

        info_wlan = dict()
        info_wlan['bytes'] = si.ifinfo(self.model.wlan_interface)
        self.model.publish('net-wlan0', info_wlan)

    def _modem_setup(self, m):
        logger.info("enabling signal query")
        if m:
            self.modem_setup_done = True
        else:
            logger.info("modem not yet ready")

    def _modem(self):
        info = dict()
        m = MM.modem(self.model.wwan_imei)
        if m:
            if not self.modem_setup_done:
                self._modem_setup(m)

            info['modem-id'] = str(m.id)

            info['vendor'] = m.vendor()
            info['model'] = m.model()
            info['revision'] = m.revision()
            info['imei'] = m.imei()

            state = m.state()
            access_tech = m.access_tech()
            access_tech2 = m.access_tech2()

            info['state'] = state
            info['access-tech'] = access_tech
            if access_tech2:    # Optional 2nd access tech, i.e. lte and 5gnr
                info['access-tech2'] = access_tech2

            loc_info = m.location()
            if loc_info is not None and loc_info['mcc']:
                info['location'] = loc_info

            sq = m.signal_quality()
            info['signal-quality'] = sq

            # FN990 reports LTE and 5G as 2nd technology
            if access_tech == '5gnr' or access_tech2 == '5gnr':
                sig = m.signal_5g()
                info['signal-5g'] = sig

            if access_tech == 'lte':
                sig = m.signal_lte()
                info['signal-lte'] = sig

            if access_tech == 'umts':
                sig = m.signal_umts()
                info['signal-umts'] = sig

            b = m.bearer()
            if b:
                info['bearer-id'] = str(b.id)
                ut = b.uptime()
                if ut:
                    info['bearer-uptime'] = ut
                ip = b.ip()
                if ip:
                    info['bearer-ip'] = ip

            s = m.sim()
            if s:
                info['sim-id'] = str(s.id)

                imsi = s.imsi()
                info['sim-imsi'] = imsi
                iccid = s.iccid()
                info['sim-iccid'] = iccid
        else:
            self.modem_setup_done = False

        self.model.publish('modem', info)
        # print(f'*** {info}')

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
