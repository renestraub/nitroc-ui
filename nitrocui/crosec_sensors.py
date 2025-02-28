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
    def sensors_present() -> bool:
        return path.exists(CrosEcSensors.BIN)

    def __init__(self):
        super().__init__()

        self.volt_in_mv = None
        self.volt_rtc_mv = None
    
    def poll(self) -> None:
        try:
            cp = subprocess.run([CrosEcSensors.BIN, "sensor", "all"], stdout=subprocess.PIPE)
            res = cp.stdout.decode().strip()
            self.volt_in_mv = self._extract_voltage(res, 'psu input voltage')
            self.volt_rtc_mv = self._extract_voltage(res, 'backup voltage')
        except FileNotFoundError:
            self.volt_in_mv = 0
            self.volt_rtc_mv = 0

    def input_voltage(self) -> float | None:
        return self.volt_in_mv / 1000.0 if self.volt_in_mv else None

    def rtc_voltage(self) -> float | None:
        return self.volt_rtc_mv / 1000.0 if self.volt_rtc_mv else None

    def bootloader_version(self) -> str:
        version = "unknown"
        try:
            cp = subprocess.run([CrosEcSensors.BIN, "version"], stdout=subprocess.PIPE)
            res = cp.stdout.decode().strip()
            pattern = rf"RO version:\s+(.*)"
            match = re.search(pattern, res)
            if match:
                version = match.group(1)
        except FileNotFoundError:
            pass
        return version

    def _extract_voltage(self, res, sensor) -> float | None:
        pattern = rf"Name: {re.escape(sensor)}\n\s*Value: ([-+]?\d+.\d+)"
        match = re.search(pattern, res, re.MULTILINE)
        # print(f'**** {match} ***')
        return float(match.group(1)) if match else None
