import subprocess


class SysInfoBase():
    def __init__(self):
        pass

    def poll(self):
        pass

    def serial(self) -> str:
        with open('/sys/class/net/eth0/address') as f:
            res = f.readline().strip().upper()
        return res

    def version(self) -> str:
        # TODO: Issues file might look totally different on Embedded platforms
        with open('/etc/issue') as f:
            res = f.readline()
            res = res.replace('\\n', '')
            res = res.replace('\\l', '')
            res = res.strip()
        return res

    def hw_version(self) -> str:
        # TODO: Not yet available
        return "0.1.0"

    def start_reason(self) -> str:
        # TODO: Not yet available
        return "unknown"

    def meminfo(self) -> tuple[int, int]:
        try:
            with open('/proc/meminfo') as f:
                res = f.readlines()
                for line in res:
                    if 'MemTotal' in line:
                        total = int(line.split()[1].strip())
                    elif 'MemFree' in line:
                        free = int(line.split()[1].strip())
            return total, free
        except FileNotFoundError:
            return (0, 0)

    def part_size(self, partition):
        cp = subprocess.run(['/usr/bin/df', '-h', partition], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        for line in res.splitlines():
            if partition in line:
                res = line
        return res

    def emmc_wear(self) -> tuple[float, float]:
        """
        Check for following output in mmc command
        eMMC Life Time Estimation A [EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A]: 0x01
        """
        try:
            cp = subprocess.run(['/usr/bin/mmc', 'extcsd', 'read', '/dev/mmcblk0'], stdout=subprocess.PIPE)
            res = cp.stdout.decode().strip()
        except FileNotFoundError:
            res = ""

        res_a = 0.0
        res_b = 0.0
        for line in res.splitlines():
            if 'Life Time Estimation' in line:
                if 'TYP_A' in line:
                    res_a = int(line[-2:], 16) * 10.0
                if 'TYP_B' in line:
                    res_b = int(line[-2:], 16) * 10.0

        return res_a, res_b

    def load(self) -> list[str]:
        with open('/proc/loadavg') as f:
            res = f.readline()
            info = res.split()
            return info[0:3]

    def cpufreq(self, core) -> int:
        with open(f'/sys/bus/cpu/devices/cpu{core}/cpufreq/scaling_cur_freq') as f:
            res = f.readline()
            return int(res)

    def date(self) -> str:
        cp = subprocess.run(['/usr/bin/date'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        return res

    def uptime(self) -> str:
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
