from time import sleep


# TODO: Remember last setting, don't change config, avoid sleep if no change

class PAC1921():
    TEMP_REG = 0x00

    def __init__(self, i2c, addr, shunt_resistance_in_ohms) -> None:
        self.i2c = i2c
        self.addr = addr
        self.rshunt = shunt_resistance_in_ohms

        # Shadow registers

        # Config gain
        # - Both ADC in 11 bit mode
        # - DI Gain = 1
        # - DV Gain = 1
        self.gain_cfg_val = 0b11_000_000

        # Integration Config
        # - 1 sample
        # - Vsense post filter on
        # - Vbus post filter on
        # - INT_EN override enabled
        # - Integration state
        self.integ_cfg_val = 0b00001111

        # Control
        # - Vpower pin controlled mode
        # - 3V full scale
        # - timeout disabled
        # - normal op
        # - forced read mode (sleep override)
        # - recalculate dac update
        self.ctrl_val = 0b00000011

        self.last_cfg = ''

    def id(self) -> None:
        prod_id = self.__getreg8(0xFD)
        print(f'product id  : 0x{prod_id:02X}')
        manu_id = self.__getreg8(0xFE)
        print(f'mfct id     : 0x{manu_id:02X}')
        revision = self.__getreg8(0xFF)
        print(f'revision    : 0x{revision:02X}')

    def start(self) -> None:
        # Set chip in read state to change configuration
        self.__setreg8(0x01, self.integ_cfg_val & 0x01)

        # Config gain
        self.__setreg8(0x00, self.gain_cfg_val)
        # Control
        self.__setreg8(0x02, self.ctrl_val)
        # Integration
        self.__setreg8(0x01, self.integ_cfg_val)

    def config(self) -> None:
        gain = self.__getreg8(0x00)
        print(f'gain        : 0x{gain:02X}')
        integration = self.__getreg8(0x01)
        print(f'integration : 0x{integration:02X}')
        ctrl = self.__getreg8(0x02)
        print(f'ctrl        : 0x{ctrl:02X}')

    def voltage(self) -> float:
        # control byte -> select data type Vbus
        sel_vbus = 0b10
        self.__setreg8(0x02, (sel_vbus << 6) | self.ctrl_val)

        # Integration control -> 4 samples
        smpl_4 = 0b0010
        self.__setreg8(0x01, (smpl_4 << 4) | self.integ_cfg_val)

        # Worst case integration period = 3.43 ms
        # TODO: why do we see 0 values with 5 ms sleep?
        sleep(0.01)

        volt_raw = self.__getreg16(0x10) >> 6
        volt = volt_raw * 32.0 / 1024

        self.last_cfg = 'voltage'

        return volt

    def current(self) -> float:
        # control byte -> select data type Vsense (aka current)
        sel_vsense = 0b01
        self.__setreg8(0x02, (sel_vsense << 6) | self.ctrl_val)

        # Integration control -> 4 samples
        smpl_4 = 0b0010
        self.__setreg8(0x01, (smpl_4 << 4) | self.integ_cfg_val)

        # Worst case integration period = 3.43 ms
        # TODO: why do we see 0 values with 5 ms sleep?
        sleep(0.01)

        vsense_raw = self.__getreg16(0x12) >> 6
        current = vsense_raw * (0.1 / self.rshunt) / 1024

        self.last_cfg = 'current'

        return current

    def power(self):
        if self.last_cfg != 'power':
            # control byte -> select data type Vpower
            sel_vpower = 0b11
            self.__setreg8(0x02, (sel_vpower << 6) | self.ctrl_val)

            # Integration control -> 4 samples
            smpl_4 = 0b0010
            self.__setreg8(0x01, (smpl_4 << 4) | self.integ_cfg_val)

            # Worst case integration period = 6.79 ms
            sleep(0.01)

        vpower_raw = self.__getreg16(0x1D) >> 6
        vsense = (vpower_raw * 32 ) * (0.1 / self.rshunt) / 1024

        self.last_cfg = 'power'

        return vsense

    def __getreg8(self, reg: int) -> int:
        self.i2c.set_addr(self.addr)
        data = self.i2c.read_reg8(reg, 1)
        return data[0]

    def __getreg16(self, reg: int) -> int:
        self.i2c.set_addr(self.addr)
        res = self.i2c.read_reg8(reg, 2)
        # print(res[0], res[1])
        value = (res[0] << 8) | (res[1] << 0)
        return value

    def __setreg8(self, reg: int, value: int) -> None:
        # print(f'Set reg {reg:02x} to {value:02x}')
        self.i2c.set_addr(self.addr)
        self.i2c.write_reg8(reg, value)
