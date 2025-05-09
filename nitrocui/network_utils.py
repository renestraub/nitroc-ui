import dbus


# apt install cmake
# apt install libdbus-1-dev
# pip install dbus-python --break-system-packages


def network_check():
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
