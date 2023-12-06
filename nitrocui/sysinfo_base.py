import subprocess


class SysInfoBase():
    def __init__(self):
        pass

    def poll(self):
        pass

    def serial(self):
        with open('/sys/class/net/eth0/address') as f:
            res = f.readline().strip().upper()

        return res

    def version(self):
        with open('/etc/issue') as f:
            res = f.readline()
            res = res.replace('\\n', '')
            res = res.replace('\\l', '')
            res = res.strip()
        return res

    def bootloader_version(self):
        # with open('/proc/device-tree/nm,bootloader,version') as f:
        #     res = f.readline().strip()
        #     res = res.rstrip('\x00')

        res = "0.0.1"
        return res

    def hw_version(self):
        # with open('/proc/device-tree/nm,carrierboard,version') as f:
        #     res = f.readline().strip()
        #     res = res.rstrip('\x00')

        res = "0.1.0"
        return res

    def start_reason(self):
        # try:
        #     with open('/sys/kernel/broker/start-reason') as f:
        #         res = f.readline().strip()

        #     return res
        # except FileNotFoundError:
        #     return "unknown"
        return "unknown"

    def meminfo(self):
        with open('/proc/meminfo') as f:
            res = f.readlines()
            for line in res:
                if 'MemTotal' in line:
                    total = int(line.split()[1].strip())
                elif 'MemFree' in line:
                    free = int(line.split()[1].strip())

        return total, free

    def part_size(self, partition):
        cp = subprocess.run(['/usr/bin/df', '-h', partition], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        for line in res.splitlines():
            if partition in line:
                res = line

        return res

    def emmc_wear(self):
        """
        Check for following output in mmc command
        eMMC Life Time Estimation A [EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A]: 0x01
        """
        cp = subprocess.run(['/usr/bin/mmc', 'extcsd', 'read', '/dev/mmcblk0'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()

        res_a = 0
        res_b = 0
        for line in res.splitlines():
            if 'Life Time Estimation' in line:
                if 'TYP_A' in line:
                    res_a = int(line[-2:], 16) * 10.0
                if 'TYP_B' in line:
                    res_b = int(line[-2:], 16) * 10.0

        return res_a, res_b

    def load(self):
        with open('/proc/loadavg') as f:
            res = f.readline()
            info = res.split()
            return info[0:3]

    def date(self):
        cp = subprocess.run(['/usr/bin/date'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        return res

    def uptime(self):
        cp = subprocess.run(['/usr/bin/uptime'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        start = res.find("up")
        end = res.find(",  load")
        return res[start:end]

    def ifinfo(self, name):
        try:
            rxpath = f'/sys/class/net/{name}/statistics/rx_bytes'
            with open(rxpath) as f:
                rxbytes = f.readline().strip()

            txpath = f'/sys/class/net/{name}/statistics/tx_bytes'
            with open(txpath) as f:
                txbytes = f.readline().strip()

        except FileNotFoundError:
            rxbytes, txbytes = None, None

        return rxbytes, txbytes
