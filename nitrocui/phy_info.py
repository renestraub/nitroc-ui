import logging
import os
import re
import subprocess

logger = logging.getLogger('vcu-ui')


class PhyInfo:
    def __init__(self, interface):
        self.__if = interface

        try:
            # Check phydev entry which contains phy_id at end
            # ../../../../../../4a100000.ethernet/4a101000.mdio/mdio_bus/4a101000.mdio/4a101000.mdio:03
            if_node = f'/sys/class/net/{self.__if}/phydev'
            link_to_phy_dev = os.readlink(if_node)
            phy_id = link_to_phy_dev.split(':')[1]

            self.__sys_node = '/sys/bus/mdio_bus/devices/4a101000.mdio:{}/configuration/'.format(phy_id)

        except FileNotFoundError:
            logger.warning(f'Cannot find {self.__if} information')
            self.__sys_node = None

    def state(self):
        if self.__sys_node:
            link = 'down'

            with open(self.__sys_node + 'link_status') as f:
                link = f.readline().strip()

            return link

    def quality(self):
        if self.__sys_node:
            qual = 0

            with open(self.__sys_node + 'snr_class') as f:
                quality = f.readline().strip()

                if 'Class A' in quality:
                    qual = 0
                elif 'Class B' in quality:
                    qual = 16
                elif 'Class C' in quality:
                    qual = 33
                elif 'Class D' in quality:
                    qual = 50
                elif 'Class E' in quality:
                    qual = 66
                elif 'Class F' in quality:
                    qual = 83
                elif 'Class G' in quality:
                    qual = 100

            return qual


class PhyInfo5:
    """
    PhyInfo implementation for kernel 5
    - phy information is no more available in sysfs, use ethtool instead
    """
    def __init__(self, interface):
        self.__if = interface
        self.p_link = re.compile(r'.*Link detected: (.*)')
        self.p_qual = re.compile(r'.*SQI: (\d)\/(\d)')

    def state(self):
        text = self.ethtool()
        res = self.p_link.findall(text)

        if res[0] == 'yes':
            return 'up'
        else:
            return 'down'

    def quality(self):
        text = self.ethtool()
        res = self.p_qual.findall(text)
        qual = float(res[0][0])
        max_qual = float(res[0][1])

        return int((qual/max_qual)*100.0)

    def ethtool(self):
        cp = subprocess.run(['/usr/sbin/ethtool', self.__if], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()

        return res
