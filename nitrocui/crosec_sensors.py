import re
import subprocess
from os import path

from .sysinfo_base import SysInfoBase


class CrosEcSensors(SysInfoBase):
    """
    System Info implementation using 'ectool' tool to retrieve values
    """
    BIN = '/usr/bin/ectool'

    @staticmethod
    def sensors_present():
        return path.exists(CrosEcSensors.BIN)

    def __init__(self):
        super().__init__()

        self.data = None
        self.volt_in_mv = 0.0
        self.volt_rtc_mv = 0.0
    
    def poll(self):
        try:
            cp = subprocess.run([CrosEcSensors.BIN, "sensor", "all"], stdout=subprocess.PIPE)
            res = cp.stdout.decode().strip()
            self.volt_in_mv = self._extract(res, 'psu input voltage')
            self.volt_rtc_mv = self._extract(res, 'backup voltage')
        except FileNotFoundError:
            self.volt_in_mv = 0
            self.volt_rtc_mv = 0

    def input_voltage(self):
        return self.volt_in_mv / 1000.0

    def rtc_voltage(self):
        return self.volt_rtc_mv / 1000.0

    def _extract(self, res, sensor):
        pattern = rf"Name: {re.escape(sensor)}\n\s*Value: ([-+]?\d+.\d+)"
        match = re.search(pattern, res, re.MULTILINE)
        # print(f'**** {match} ***')
        if match:
            return float(match.group(1))
        else:
            return 0
