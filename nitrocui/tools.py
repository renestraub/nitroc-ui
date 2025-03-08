import ipaddress
import subprocess


NMCLI_BIN = '/usr/bin/nmcli'


def secs_to_hhmm(secs):
    t = int((secs + 30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


# def ping(ip):
#     cp = subprocess.run(['/usr/bin/ping', '-c', '4', ip], stdout=subprocess.PIPE)
#     res = cp.stdout.decode()

#     return res


# def nmcli_c():
#     cp = subprocess.run([NMCLI_BIN, 'c'], stdout=subprocess.PIPE)
#     res = cp.stdout.decode()

#     return res


def nmcli_network_check():
    """
    Check level of internet access

    returns:
    full: You have internet access.
    limited: You have a network connection but no full internet access.
    portal: The connection is behind a captive portal (e.g., hotel WiFi login page).
    none: No network connectivity.
    unknown: The status is not known.    
    """
    cp = subprocess.run([NMCLI_BIN, 'networking', 'connectivity', 'check'], stdout=subprocess.PIPE)
    if cp.returncode == 0:
        res = cp.stdout.decode().strip()
        return res
    else:
        return 'unknown'


def is_valid_ipv4(address):
    try:
        ipaddress.IPv4Address(address)
        return True  # It's a valid IPv4 address
    except ipaddress.AddressValueError:
        return False  # It's not a valid IPv4 address
