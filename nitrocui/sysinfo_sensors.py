import re
import subprocess
from os import path

from nitrocui.sysinfo_base import SysInfoBase


class SysInfoSensors(SysInfoBase):
    """
    System Info implementation using 'sensors' tool to retrieve values
    """
    BIN = '/usr/bin/sensors'

    @staticmethod
    def sensors_present():
        return path.exists(SysInfoSensors.BIN)

    def __init__(self):
        super().__init__()

        self.data = None
        self.temp_mb1 = None
        self.temp_mb2 = None
        self.temp_eth = None
        self.volt_in = None
        self.volt_rtc = None

    def poll(self):
        cp = subprocess.run([SysInfoSensors.BIN], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        self.sensor_res = res
        # print(res)

        self.temp_mb1 = self._extract('lm75-i2c-0-48', 'temp1')
        self.temp_mb2 = self._extract('lm75-i2c-0-49', 'temp1')
        self.temp_eth = self._extract('lm75-i2c-8-48', 'temp1')

        self.volt_in = '20.0' # self._extract('input-voltage')
        self.volt_rtc = '20.0' # self._extract('rtc-voltage')

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
                groupNum = 1
                print ("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
                return float(match.group(1))