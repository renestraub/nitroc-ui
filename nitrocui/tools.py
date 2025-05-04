import dbus
import ipaddress

# apt install cmake
# apt install libdbus-1-dev
# pip install dbus-python --break-system-packages


def secs_to_hhmm(secs):
    t = int((secs + 30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


def dbus_network_check():
    """
    Check the level of internet access using D-Bus and NetworkManager.

    Returns:
    full: You have internet access.
    limited: You have a network connection but no full internet access.
    portal: The connection is behind a captive portal (e.g., hotel WiFi login page).
    none: No network connectivity.
    unknown: The status is not known.
    """
    try:
        # Connect to the system bus
        bus = dbus.SystemBus()

        # Get the NetworkManager object
        network_manager = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")

        # Call the CheckConnectivity method
        connectivity = network_manager.Get(
            "org.freedesktop.NetworkManager",
            "Connectivity",
            dbus_interface="org.freedesktop.DBus.Properties"
        )

        # Map the connectivity result to human-readable strings
        connectivity_map = {
            4: "full",      # Full internet access
            3: "limited",   # Limited internet access
            2: "portal",    # Captive portal
            1: "none",      # No connectivity
            0: "unknown"    # Unknown status
        }

        return connectivity_map.get(connectivity, "unknown") if isinstance(connectivity, int) else "unknown"
    except dbus.DBusException as e:
        return "unknown"


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
