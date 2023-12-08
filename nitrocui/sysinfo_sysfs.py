from os import path

from .sysinfo_base import SysInfoBase


class SysInfoSysFs(SysInfoBase):
    """
    System Info implementation using sys-fs to retrieve values
    """
    def __init__(self):
        super().__init__()

        # Locate PMIC hwmon

        # From kernel 5.10.x on, PMIC path changes to the following
        # /sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon/hwmon/hwmon1/
        path_5_10 = '/sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon/hwmon/hwmon1/'
        if path.exists(path_5_10):
            self.da9063_path = path_5_10
        else:
            self.da9063_path = '/sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon'

        # Optional LM75 sensor (NG800 devices)
        self.lm75_path = '/sys/bus/i2c/drivers/lm75/1-0048/hwmon/hwmon1'

    def temperature(self):
        with open(f'{self.da9063_path}/temp1_input') as f:
            temp_in_milli_c = f.readline().strip()
            return round(float(temp_in_milli_c) / 1000.0, 1)

    def input_voltage(self):
        with open(f'{self.da9063_path}/in1_input') as f:
            adc_millivolts = f.readline().strip()
            return round(float(adc_millivolts) / 1000.0 * 15.0, 1)

    def rtc_voltage(self):
        with open(f'{self.da9063_path}/in4_input') as f:
            adc_millivolts = f.readline().strip()
            return round(float(adc_millivolts) / 1000.0, 3)

    def temperature_lm75(self):
        # TODO: Test
        try:
            with open(f'{self.lm75_path}/temp_input') as f:
                temp_in_milli_c = f.readline().strip()
                return round(float(temp_in_milli_c) / 1000.0, 1)
        except FileNotFoundError:
            pass
