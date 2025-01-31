import ipaddress
import subprocess


def secs_to_hhmm(secs):
    t = int((secs + 30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


# def ping(ip):
#     cp = subprocess.run(['/usr/bin/ping', '-c', '4', ip], stdout=subprocess.PIPE)
#     res = cp.stdout.decode()

#     return res


def nmcli_c():
    cp = subprocess.run(['/usr/bin/nmcli', 'c'], stdout=subprocess.PIPE)
    res = cp.stdout.decode()

    return res


def is_valid_ipv4(address):
    try:
        ipaddress.IPv4Address(address)
        return True  # It's a valid IPv4 address
    except ipaddress.AddressValueError:
        return False  # It's not a valid IPv4 address
