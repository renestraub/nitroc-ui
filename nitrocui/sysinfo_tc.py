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

        for bus in [10, 11]:
            self.i2c_bus[bus] = I2C(bus)
            self.i2c_bus[bus].open()

        self._tc1 = MCP9600(self.i2c_bus[10], address = 0x67, tctype = 'T', tcfilter=4)

        ver = self._tc1.version
        logger.info(f'MCP9600 id: {(ver>>4) & 0xF}.{(ver>>0) & 0xF}')

    def temp_tc(self):
        return self._tc1.temperature
