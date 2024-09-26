from .sysinfo_base import SysInfoBase
from .i2c import I2C
from .pac1921 import PAC1921


class SysInfoPower(SysInfoBase):
    """
    System Info implementation using PAC1921 power sensors
    """
    FOLDER = '/sys/class/thermal/'

    def __init__(self):
        super().__init__()

        self.i2c_bus = dict()
        self.sensors = dict()
        self.powers = dict()

        for bus in [0, 4, 5, 6, 7, 8]:
            self.i2c_bus[bus] = I2C(bus)
            self.i2c_bus[bus].open()

        self.sensors['mb'] = PAC1921(self.i2c_bus[0], 0x4C, 0.005)
        self.sensors['nmcf1'] = PAC1921(self.i2c_bus[4], 0x4C, 0.020)
        self.sensors['nmcf2'] = PAC1921(self.i2c_bus[5], 0x4C, 0.020)
        self.sensors['nmcf3'] = PAC1921(self.i2c_bus[6], 0x4C, 0.020)
        self.sensors['nmcf4'] = PAC1921(self.i2c_bus[7], 0x4C, 0.020)
        self.sensors['eth'] = PAC1921(self.i2c_bus[8], 0x4C, 0.005)

        for _, sensor in self.sensors.items():
            try:
                # sensor.id()
                sensor.start()
            except:
                pass

    def poll(self):
        for name in ['mb', 'eth', 'nmcf1', 'nmcf2', 'nmcf3', 'nmcf4']:
            self.powers[name] = self._get_pwr(name)

        # Mainboard sensor also includes NMCF slots, subtract these values to get mainboard alone
        pwr_slots = 0.0
        for slot in range(1, 5):
            name = f'nmcf{slot}'
            if name in self.powers and self.powers[name] is not None:
                pwr_slots += self.powers[name]

        self.powers['mb'] -= pwr_slots

    def pwr_mb(self):
        # return self._get_pwr('mb')
        return self.powers['mb']

    def pwr_eth(self):
        return self.powers['eth']

    def pwr_nmcf1(self):
        return self.powers['nmcf1']

    def pwr_nmcf2(self):
        return self.powers['nmcf2']

    def pwr_nmcf3(self):
        return self.powers['nmcf3']

    def pwr_nmcf4(self):
        return self.powers['nmcf4']

    def _get_pwr(self, name) -> float | None:
        try:
            pwr = self.sensors[name].power()
            return pwr
        except OSError:
            return None
