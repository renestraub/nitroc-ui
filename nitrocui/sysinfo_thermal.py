from os import path

from .sysinfo_base import SysInfoBase


class SysInfoThermal(SysInfoBase):
    """
    System Info implementation using thermal subsystem
    """
    FOLDER = '/sys/class/thermal/'

    def __init__(self):
        super().__init__()

        """
        root@localhost:~/sysinfo# cat /sys/class/thermal/thermal_zone1/type
        ap-cpu0-thermal
        root@localhost:~/sysinfo# cat /sys/class/thermal/thermal_zone2/type
        ap-cpu1-thermal
        root@localhost:~/sysinfo# cat /sys/class/thermal/thermal_zone3/type
        ap-cpu2-thermal
        root@localhost:~/sysinfo# cat /sys/class/thermal/thermal_zone4/type
        ap-cpu3-thermal
        """

        self.ap = SysInfoThermal.FOLDER + 'thermal_zone0/'
        self.cp0 = SysInfoThermal.FOLDER + 'thermal_zone5/'
        self.cp2 = SysInfoThermal.FOLDER + 'thermal_zone6/'

    def temp_ap(self) -> float:
        return self._read_temp(self.ap)

    def temp_cp0(self) -> float:
        # TODO: 20241204 - Currently not working
        return self._read_temp(self.cp0)

    def temp_cp2(self) -> float:
        # TODO: 20241204 - Currently not working
        return self._read_temp(self.cp2)

    def _read_temp(self, path: str) -> float:
        """Helper method to read temperature from a given path."""
        try:
            with open(f'{path}/temp') as f:
                temp_in_milli_c = f.readline().strip()
                return round(float(temp_in_milli_c) / 1000.0, 1)
        except FileNotFoundError:
            return 0.0
