import ipaddress
import subprocess


NMCLI_BIN = '/usr/bin/nmcli'


def secs_to_hhmm(secs):
    t = int((secs + 30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


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


def format_size(bytes: int) -> str:
    """
    Convert a size in bytes to a human-readable string with GB, MB, KB, or Bytes.
    
    :param bytes: The size in bytes.
    :return: A formatted string representing the size.
    """
    KB = 1024
    MB = 1024*1024
    GB = 1024*1024*1024
    TB = 1024*1024*1024*1024

    if bytes >= TB:
        return f"{bytes / TB:.2f} TB"
    elif bytes >= GB:
        return f"{bytes / GB:.2f} GB"
    elif bytes >= MB:
        return f"{bytes / MB:.2f} MB"
    elif bytes >= KB:
        return f"{bytes / KB:.2f} KB"
    else:
        return f"{bytes} Bytes"


def format_frequency(hz: int) -> str:
    """
    Convert a frequency in Hz to a human-readable string with GHz or MHz.
    
    :param hz: The frequency in Hz.
    :return: A formatted string representing the frequency.
    """
    if hz >= 1_000_000_000:
        return f"{hz / 1_000_000_000:.1f} GHz"
    elif hz >= 1_000_000:
        return f"{hz / 1_000_000:.0f} MHz"
    elif hz >= 1_000:
        return f"{hz / 1_000:.0f} kHz"
    else:
        return f"{hz} Hz"
