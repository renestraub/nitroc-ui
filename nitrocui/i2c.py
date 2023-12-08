"""
This module provides a class for I2C communication. It uses the /dev/i2c-n devices to operate
"""
import os
import fcntl

I2C_SLAVE = 0x0703

class I2C:
    """
    I2C class represnting one device
    """
    def __init__(self, bus):
        self.bus = bus
        self.fd = None

    def open(self):
        """
        Open the I2C device
        """
        self.fd = os.open(f'/dev/i2c-{self.bus}', os.O_RDWR)

    def close(self):
        """
        Close the I2C device
        """
        os.close(self.fd)

    def set_addr(self, addr):
        """
        Set the address of the device
        """
        fcntl.ioctl(self.fd, I2C_SLAVE, addr)

    def write(self, data):
        """
        Write data over i2c
        """
        os.write(self.fd, bytes(data))

    def read(self, length):
        """
        Read data over i2c
        """
        return os.read(self.fd, length)

    def read_reg8(self, reg, length):
        """
        Read from a 8 bit addressable register
        """
        self.write([reg])
        return self.read(length)

    def write_reg8(self, reg, data):
        """
        Write to a 8 bit addressable register
        """
        self.write([reg, data])
