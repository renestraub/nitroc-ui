import logging

from .sysinfo_base import SysInfoBase
from .i2c import I2C
from .mcp9600 import MCP9600


logger = logging.getLogger('nitroc-ui')


class SysInfoTC(SysInfoBase):
    """
    System Info implementation using MCP9600 via I2C
    """

    ADDRESS = 0x67

    def __init__(self):
        super().__init__()

        self.i2c_bus = dict()
        self.sensors = []
        self.present = 0    # Bitmask with detected sensors

        # New IO Env module. 8 thermal sensors ;-)
        for bus in [10]:
            self.i2c_bus[bus] = I2C(bus)
            self.i2c_bus[bus].open()

        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x60, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x61, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x62, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x63, tctype = 'T', tcfilter=4))
        # self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x64, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x65, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x66, tctype = 'T', tcfilter=4))
        self.sensors.append(MCP9600(self.i2c_bus[10], address = 0x67, tctype = 'T', tcfilter=4))

        # Probe sensors
        pos = 0
        for s in self.sensors:
            try:
                # Try sensor, remember in <present> variable
                # print(f"trying pos {pos}")
                s.init()
                self.present |= (1 << pos)
                logger.info(f'Detected thermopcouple {pos} at 0x{s.ADDR:02x}')
            except OSError:
                # Silently ignore for the moment
                pass
            pos += 1

    def temp_tc(self, which):
        # print("checking TC")
        if self.present & (1 << which):
            temp = self.sensors[which].temperature()
        else:
            temp = None
        return temp
