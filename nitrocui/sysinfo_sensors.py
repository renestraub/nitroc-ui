import re
import subprocess
from os import path

from .sysinfo_base import SysInfoBase


class SysInfoSensors(SysInfoBase):
    """
    System Info implementation using 'sensors' tool to retrieve values
    """
    BIN = '/usr/bin/sensors'

    @staticmethod
    def sensors_present():
        return path.exists(SysInfoSensors.BIN)

    def __init__(self):
        # TODO: Check Ethernet board variant?
        super().__init__()

        self.data = None
        self.volt_in = None
        self.volt_rtc = None
        self.temp_mb1 = None
        self.temp_mb2 = None
        self.temp_eth = None
        self.temp_nmcf1 = None
        self.temp_nmcf2 = None
        self.temp_nmcf3 = None
        self.temp_nmcf4 = None
        self.temp_phy1 = None
        self.temp_phy2 = None
        self.temp_phy3 = None
        self.temp_eth_switch = None
        self.temp_nvm_sdd = None
        self.temp_nvm_sdd = None
        self.temp_wle3000 = None


    def poll(self):
        cp = subprocess.run([SysInfoSensors.BIN], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        self.sensor_res = res

        self.volt_in = '20.0' # self._extract('input-voltage')
        self.volt_rtc = '3.0' # self._extract('rtc-voltage')

        self.temp_mb1 = self._extract('lm75-i2c-0-48', 'temp1')
        self.temp_mb2 = self._extract('lm75-i2c-0-49', 'temp1')
        self.temp_eth = self._extract('lm75-i2c-8-48', 'temp1')
        self.temp_nmcf1 = self._extract('lm75-i2c-4-4c', 'temp1')
        self.temp_nmcf2 = self._extract('lm75-i2c-5-4c', 'temp1')
        self.temp_nmcf3 = self._extract('lm75-i2c-6-4c', 'temp1')
        self.temp_nmcf4 = self._extract('lm75-i2c-7-4c', 'temp1')

        # 2.5 GB PHYs
        self.temp_phy1 = self._extract('f212a600.mdio_mii:01-mdio-1', 'temp1')
        self.temp_phy2 = self._extract('f212a600.mdio_mii:09-mdio-9', 'temp1')
        self.temp_phy3 = self._extract('f212a600.mdio_mii:11-mdio-b', 'temp1')

        # Averaged temperature of 1G ETH Switch
        phy_temps = 0
        phy_ids = [3, 4, 5, 6, 7]
        for phy_num in phy_ids:
            phy_temp = self._extract(f'cp0configspacef2000000mdio12a200switch16mdio0{phy_num}-mdio-{phy_num}', 'temp1')
            if phy_temp:
                phy_temps += phy_temp

        self.temp_eth_switch = phy_temps / len(phy_ids)

        # pci-40100, pci-20100 seem to denote location oin PCI system.
        # could use this pattern to bind values to a NMCF slot. Would need a reg-ex like lookup
        self.temp_nvm_sdd = self._extract('nvme-pci-40100', 'Composite')

        # self.temp_wle3000_1 = self._extract('ath11k_hwmon-pci-20100', 'temp1')
        self.temp_wle3000 = self._extract('ath11k_hwmon-pci.*', 'temp1')  # Find WLE3000 in any slot
        # print(f"wle3000 {self.temp_wle3000}")

    def input_voltage(self):
        return self.volt_in

    def rtc_voltage(self):
        return self.volt_rtc

    def temperature_mb1_pcb(self):
        return self.temp_mb1

    def temperature_mb2_pcb(self):
        return self.temp_mb2

    def temperature_eth_pcb(self):
        return self.temp_eth

    def temperature_nmcf1_pcb(self):
        return self.temp_nmcf1

    def temperature_nmcf2_pcb(self):
        return self.temp_nmcf2

    def temperature_nmcf3_pcb(self):
        return self.temp_nmcf3

    def temperature_nmcf4_pcb(self):
        return self.temp_nmcf4

    def temperature_phy1(self):
        return self.temp_phy1

    def temperature_phy2(self):
        return self.temp_phy2

    def temperature_phy3(self):
        return self.temp_phy3

    def temperature_eth_switch(self):
        return self.temp_eth_switch

    def temperature_nvm_ssd(self):
        return self.temp_nvm_sdd

    def temperature_wifi_wle3000(self):
        return self.temp_wle3000

    def _extract(self, sensor, token):
        regex = rf"{sensor}\nAdapter.*\n{token}:\s*([-+]?\d+.\d+)"
        # match = re.search(regex, self.sensor_res, re.MULTILINE)
        # print(len(match.groups()))
        # print(match)
        # if match and len(match.groups()) == 3:
        #     return float(match.group(3))

        matches = re.finditer(regex, self.sensor_res, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            # print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
            if len(match.groups()) == 1:
                # groupNum = 1
                # print ("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
                return float(match.group(1))
