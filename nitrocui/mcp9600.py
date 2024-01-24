import time

# Inspired by https://github.com/CurlyTaleGamesLLC/Adafruit_MicroPython_MCP9600/blob/main/adafruit_mcp9600.py

_DEFAULT_ADDRESS = 0x67

_REGISTER_HOT_JUNCTION = 0x00
_REGISTER_COLD_JUNCTION = 0x02
_REGISTER_THERM_CFG = 0x05
_REGISTER_DEVICE_CFG = 0x06
_REGISTER_VERSION = 0x20


class MCP9600:
    # Sensor uses clock stretching to pause I2C master while getting temperature value
    # Seemingly this doesn't work properly with CN9130 I2C system. Allow some retries
    RETRIES = 3

    # Shutdown mode options
    NORMAL = 0b00
    SHUTDOWN = 0b01
    BURST = 0b10

    # Burst mode sample options
    BURST_SAMPLES_1 = 0b000
    BURST_SAMPLES_2 = 0b001
    BURST_SAMPLES_4 = 0b010
    BURST_SAMPLES_8 = 0b011
    BURST_SAMPLES_16 = 0b100
    BURST_SAMPLES_32 = 0b101
    BURST_SAMPLES_64 = 0b110
    BURST_SAMPLES_128 = 0b111

    types = ("K", "J", "T", "N", "S", "E", "B", "R")

    def __init__(self, myi2c, address=_DEFAULT_ADDRESS, tctype="K", tcfilter=0):
        self.buf = bytearray(2)
        self.singlebyte = bytearray(1)
        self.i2c_device = myi2c
        self.ADDR = address
        self.type = tctype

        # is this a valid thermocouple type?
        if tctype not in MCP9600.types:
            raise Exception("invalid thermocouple type ({})".format(tctype))
        # filter is from 0 (none) to 7 (max), can limit spikes in
        # temperature readings
        self._tcfilter = min(7, max(0, tcfilter))
        self._ttype = MCP9600.types.index(tctype)

    def init(self):
        # Device config
        # - All defaults: 0.0625, 18 Bit resolution, 1 sample, normal mode
        self.__setreg8(_REGISTER_DEVICE_CFG, 0x00)

        # Sensor config
        self.__setreg8(_REGISTER_THERM_CFG, self._tcfilter | (self._ttype << 4))

    def version(self):
        """ MCP9600 chip version """
        data = self.__getreg8(_REGISTER_VERSION)
        return data[0]

    def ambient_temperature(self):
        """ Cold junction/ambient/room temperature in Celsius """
        data = self.__getreg16(_REGISTER_COLD_JUNCTION)
        return self.temp_c(data)

    def temperature(self):
        """ Hot junction temperature in Celsius """
        data = self.__getreg16(_REGISTER_HOT_JUNCTION)
        return self.temp_c(data)

    def temp_c(self, byteData):
        # Bit 15 = Sign
        # Bit 14 = 1024 degC
        # Bit 1 = 1/8 degC
        # Bit 0 = 1/16 degC
        temp = (((byteData[0] & 0x7F) * 16) + (byteData[1] / 16))
        if byteData[0] & 0x80:
            # Negative temp
            # TODO: Check properly
            temp -= 4096

        return temp

    def __getreg8(self, reg: int):
        # print(f'__getreg16 0x{self.ADDR:02x} 0x{reg:02x}')
        for _ in range(MCP9600.RETRIES):
            try:
                self.i2c_device.set_addr(self.ADDR)
                self.i2c_device.write([reg])
                self.__i2c_wait()
                res = self.i2c_device.read(1)
                self.__i2c_wait()
                # print(res)
                return res
            except OSError:
                # print("read error -> retry")
                pass

    def __getreg16(self, reg: int):
        # print(f'__getreg16 0x{self.ADDR:02x} 0x{reg:02x}')
        for _ in range(MCP9600.RETRIES):
            try:
                self.i2c_device.set_addr(self.ADDR)
                self.i2c_device.write([reg])
                self.__i2c_wait()
                res = self.i2c_device.read(2)
                # print(res)
                return res
            except OSError:
                print("*** read error -> retry")
                pass

    def __setreg8(self, reg: int, value: int) -> None:
        # print(f'Set reg {reg:02x} to {value:02x}')
        self.i2c_device.set_addr(self.ADDR)
        self.i2c_device.write_reg8(reg, value)

    def __i2c_wait(self):
        time.sleep(60/1_000_000)    # 60 us max. clock stretching time
