import dbus
import logging
import re  # Import regular expression module

from .cellular_signal_quality import CellularSignalQuality

logger = logging.getLogger('nitroc-ui')

# Define global constants for D-Bus interfaces
DBUS_PROPERTIES_IF = "org.freedesktop.DBus.Properties"
MM_DBUS_IF = "org.freedesktop.ModemManager1"
MM_MODEM_IF = "org.freedesktop.ModemManager1.Modem"
MM_MODEM_SIGNAL_IF = "org.freedesktop.ModemManager1.Modem.Signal"
MM_MODEM_LOCATION_IF = "org.freedesktop.ModemManager1.Modem.Location"
MM_BEARER_IF = "org.freedesktop.ModemManager1.Bearer"
MM_SIM_IF = "org.freedesktop.ModemManager1.Sim"
MM_OBJECT_MANAGER_IF = "org.freedesktop.DBus.ObjectManager"

SIG_QUALITY_CHECK_IN_SECS = 5


class MM():
    @staticmethod
    def modem(imei: str):
        id = MM._id_dbus(imei)
        if id is not None:
            return Modem(id)    # else None

    @staticmethod
    def _id_dbus(imei_regex: str) -> int | None:
        """
        Find a modem ID by matching its IMEI against a given regex.

        Args:
        imei_regex (str): A regular expression to match the modem's IMEI.

        Returns:
        int: The modem ID (D-Bus object path) if a match is found, None otherwise.
        """
        try:
            # Connect to the system bus
            bus = dbus.SystemBus()

            # Get the ModemManager object
            modem_manager = bus.get_object(MM_DBUS_IF, "/org/freedesktop/ModemManager1")

            # Get the list of modems
            modems = modem_manager.GetManagedObjects(dbus_interface=MM_OBJECT_MANAGER_IF)
            assert modems is not None, "No modems found"

            # Iterate over all modems
            for path, interfaces in modems.items():
                if MM_MODEM_IF in interfaces:
                    # Get the modem object
                    modem = bus.get_object(MM_DBUS_IF, path)

                    # Get the IMEI of the modem
                    imei = modem.Get(MM_MODEM_IF, "EquipmentIdentifier", dbus_interface=DBUS_PROPERTIES_IF)

                    # Compare the IMEI with the provided regex
                    if imei and re.fullmatch(imei_regex, imei):
                        # Extract and return the modem ID (number) from the path
                        modem_id = int(path.split('/')[-1])
                        return modem_id

            logger.info('no modem(s) matched the provided IMEI')
            return None
        except dbus.DBusException as e:
            logger.warning(f"failed to retrieve modem information: {e}")
            return None


class Modem():
    def __init__(self, id):
        self.id = id

        self.dbus = dbus.SystemBus()

        self.modem_if = self._get_modem_by_id()
        assert self.modem_if is not None, "Modem object is not initialized"

        self.signal_if = dbus.Interface(self.modem_if, MM_MODEM_SIGNAL_IF)
        assert self.signal_if is not None, "Signal interface is None"

        self.loc_if = dbus.Interface(self.modem_if, MM_MODEM_LOCATION_IF)
        assert self.loc_if is not None, "Location interface is None"

    def reset(self):
        """
        Reset the modem using the D-Bus interface.
        """
        try:
            # Ensure the modem object is initialized
            assert self.modem_if is not None, "Modem object is not initialized"

            # Create an interface pointer for the Modem interface
            modem_interface = dbus.Interface(self.modem_if, MM_MODEM_IF)
            modem_interface.Reset()
            logger.info(f"modem {self.id} has been reset successfully.")
        except dbus.DBusException as e:
            logger.warning(f"failed to reset modem {self.id}: {e}")

    def vendor(self) -> str:
        return self._get_modem_property_as_string("Manufacturer")

    def model(self) -> str:
        return self._get_modem_property_as_string("Model")

    def revision(self) -> str:
        return self._get_modem_property_as_string("Revision")

    def imei(self) -> str:
        return self._get_modem_property_as_string("EquipmentIdentifier")

    def state(self) -> str:
        assert self.modem_if is not None, "Modem object is not initialized"
        state_code = self.modem_if.Get(MM_MODEM_IF, "State", dbus_interface=DBUS_PROPERTIES_IF)
        assert state_code is not None
        return Modem.state_to_string(int(state_code))

    def access_tech(self) -> str | None:
        return self._get_access_tech_by_index(0)

    def access_tech2(self) -> str | None:
        return self._get_access_tech_by_index(1)

    def signal_quality(self) -> int:
        assert self.modem_if is not None, "Modem object is not initialized"
        sigq = self.modem_if.Get(MM_MODEM_IF, "SignalQuality", dbus_interface=DBUS_PROPERTIES_IF)
        return int(sigq[0]) if sigq is not None else 0

    def signal_5g(self):
        quality = self.get_signal_quality("Nr5g")
        assert quality is not None, "Signal quality is None"

        rsrp = quality['rsrp']
        rsrq = quality['rsrq']
        snr = quality['snr']

        if rsrp is not None and rsrq is not None and snr is not None:
            rsrp = CellularSignalQuality.limit_signal(rsrp)
            rsrq =  CellularSignalQuality.limit_rsrq(rsrq)
            snr =  CellularSignalQuality.limit_snr(snr)
            total = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)

            res = dict()
            res['rsrp'] = rsrp
            res['rsrq'] = rsrq
            res['snr'] = snr
            res['total'] = total

            return res
        else:
            logger.warning("5G signal quality metrics are not available")
            return None

    def signal_lte(self):
        """
        Retrieve and process LTE signal quality metrics.

        Returns:
        dict: A dictionary containing processed LTE signal quality metrics.
        """
        quality = self.get_signal_quality("Lte")
        assert quality is not None, "Signal quality is None"

        rsrp = quality['rsrp']
        rsrq = quality['rsrq']
        snr = quality['snr']
        rssi = quality['rssi']

        # Clamp values to valid ranges
        rsrp = CellularSignalQuality.limit_signal(rsrp)
        rsrq = CellularSignalQuality.limit_rsrq(rsrq)
        snr = CellularSignalQuality.limit_snr(snr)

        # Compute overall signal quality
        total = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)

        res = dict()
        res['rsrp'] = rsrp
        res['rsrq'] = rsrq
        res['snr'] = snr
        res['rssi'] = rssi
        res['total'] = total

        return res

    def signal_umts(self):
        res = dict()
        res['rscp'] = -120  # Fallback value for rscp
        res['ecio'] = -20

        # quality = self.get_signal_quality("Umts")
        # assert quality is not None, "Signal quality is None"

        # res = dict()
        # rscp = quality['rscp']
        # if Modem.is_valid_signal(rscp): # TODO: Add is_valid_rscp
        #     res['rscp'] = rscp
        # else:
        #     res['rscp'] = -120  # Fallback value for rscp

        # ecio = quality['ecio']
        # if Modem.is_valid_rsrq(ecio):   # TODO: Add is_valid_ecio
        #     res['ecio'] = ecio
        # else:
        #     res['ecio'] = -20

        return res

    def location(self):
        res = self.get_location()
        return res

    def bearer(self):
        assert self.modem_if is not None, "Modem object is not initialized"
        bearers = self.modem_if.Get(MM_MODEM_IF, "Bearers", dbus_interface=DBUS_PROPERTIES_IF)
        if bearers is not None and len(bearers) >= 1:
            bearer_id = int(bearers[0].split('/')[-1])
            assert 0 <= bearer_id <= 10000
            return Bearer(bearer_id)

    def sim(self):
        assert self.modem_if is not None, "Modem object is not initialized"
        sim = self.modem_if.Get(MM_MODEM_IF, "Sim", dbus_interface=DBUS_PROPERTIES_IF)
        if sim is not None and sim != '/':
            sim_id = int(sim.split('/')[-1])
            assert 0 <= sim_id <= 1000
            return SIM(sim_id)

    def _get_modem_by_id(self):
        """
        Retrieve a Modem object by its ID.

        Returns:
        Modem: A Modem object if the modem exists, None otherwise.
        """
        try:
            # Construct the D-Bus object path for the modem
            modem_path = f"/org/freedesktop/ModemManager1/Modem/{self.id}"

            # Check if the modem exists
            modem = self.dbus.get_object(MM_DBUS_IF, modem_path)
            if modem:
                modem_interface = dbus.Interface(modem, MM_MODEM_IF)
                assert modem_interface is not None, "Modem interface is None"
                return modem_interface
            else:
                logger.info(f"no modem found with ID {self.id}")
                return None
        except dbus.DBusException as e:
            logger.error(f"failed to retrieve modem by ID {self.id}: {e}")
            return None

    def get_signal_quality(self, accesstech: str) -> dict | None:
        """
        Retrieve the signal quality for a modem using D-Bus.

        Args:
        accesstech

        Returns:
        dict: A dictionary containing signal quality metrics (e.g., rsrp, rsrq, snr).
        """
        try:
            # signal_interface = dbus.Interface(self.modem_if, MM_MODEM_SIGNAL_IF)
            # assert signal_interface is not None, "Signal interface is None"

            # Enable signal monitoring (if not already enabled)
            rate: int = self.signal_if.Get(MM_MODEM_SIGNAL_IF, "Rate", dbus_interface=DBUS_PROPERTIES_IF)
            assert rate is not None
            if rate != SIG_QUALITY_CHECK_IN_SECS:
                logger.info(f"setting signal quality check interval to {SIG_QUALITY_CHECK_IN_SECS} seconds")
                self.signal_if.Setup(SIG_QUALITY_CHECK_IN_SECS)  # Set up signal monitoring

            # Retrieve the signal quality properties
            signal_properties = self.signal_if.Get(MM_MODEM_SIGNAL_IF, accesstech, dbus_interface=DBUS_PROPERTIES_IF)
            assert signal_properties is not None, "Signal properties are None"

            def to_float(value):
                """Convert a value to float, round to 1 digit, or return None if the value is None."""
                return round(float(value), 1) if value is not None else None

            # Parse the signal properties into a dictionary
            signal_quality = {
                "rsrp": to_float(signal_properties.get("rsrp")),
                "rsrq": to_float(signal_properties.get("rsrq")),
                "snr": to_float(signal_properties.get("snr")),
                "rssi": to_float(signal_properties.get("rssi"))
            }

            return signal_quality
        except dbus.DBusException as e:
            logger.warning(f"failed to retrieve signal quality: {e}")
            return None

    def get_location(self) -> dict | None:
        """
        Retrieve the location information for a modem using D-Bus.

        Returns:
        dict: A dictionary containing location information.
        """
        try:
            MM_MODEM_LOCATION_SOURCE_3GPP_LAC_CI = 1 << 0

            # loc_interface = dbus.Interface(self.modem_if, MM_MODEM_LOCATION_IF)

            # Enable location monitoring (if not already enabled)
            enabled_locs = self.loc_if.Get(MM_MODEM_LOCATION_IF, "Enabled", dbus_interface=DBUS_PROPERTIES_IF)
            assert enabled_locs is not None
            if enabled_locs & MM_MODEM_LOCATION_SOURCE_3GPP_LAC_CI == 0:
                logger.info("enabling 3GPP location query")
                self.loc_if.Setup(MM_MODEM_LOCATION_SOURCE_3GPP_LAC_CI, False)

            # Get location information
            locations = self.loc_if.GetLocation()
            if MM_MODEM_LOCATION_SOURCE_3GPP_LAC_CI in locations:
                loc_info = Modem.parse_location_string(locations[MM_MODEM_LOCATION_SOURCE_3GPP_LAC_CI])
                return loc_info

        except dbus.DBusException as e:
            logger.warning(f"failed to retrieve location info: {e}")
            return None

    @staticmethod
    def parse_location_string(location_string: str):
        """
        Parse a location string into relevant variables.

        Args:
        location_string (str): The location string to parse.

        Returns:
        dict: A dictionary containing parsed location data.
        """
        try:
            # Split the string into components
            components = location_string.split(',')

            # Extract variables
            mcc = int(components[0].strip())  # Mobile Country Code
            mnc = int(components[1].strip())  # Mobile Network Code
            lac = int(components[2].strip(), 16)  # Location Area Code (hexadecimal), 2G/3G
            tac = int(components[4].strip(), 16)  # Tracking Area Code (hexadecimal), LTE/5GNR
            cid = int(components[3].strip(), 16)  # Cell ID (hexadecimal)

            return {
                "mcc": mcc,
                "mnc": mnc,
                "lac": lac,
                "tac": tac,
                "cid": cid
            }
        except (IndexError, ValueError) as e:
            logger.warning(f"failed to parse location string: {e}")
            return None

    @staticmethod
    def state_to_string(state: int) -> str:
        """
        Convert a modem state value to a human-readable string.

        Args:
        state (int): The modem state value.

        Returns:
        str: A human-readable string representing the modem state.
        """
        state_map = {
            0: "Unknown",
            1: "Initializing",
            2: "Locked",
            3: "Disabled",
            4: "Disabling",
            5: "Enabling",
            6: "Enabled",
            7: "Searching",
            8: "Registered",
            9: "Disconnecting",
            10: "Connecting",
            11: "Connected"
        }
        return state_map.get(state, "Invalid State")

    @staticmethod
    def access_tech_to_strings(bitmask: int) -> list[str]:
        """
        Convert a bitmap result into a list of access technology strings.

        Args:
        bitmask (int): The bitmap representing access technologies.

        Returns:
        list[str]: A list of human-readable strings representing the access technologies.
        """
        access_tech_map = {
            1 << 0: "POTS",
            1 << 1: "GSM",
            1 << 2: "GSM Compact",
            1 << 3: "GPRS",
            1 << 4: "EDGE",
            1 << 5: "UMTS",
            1 << 6: "HSDPA",
            1 << 7: "HSUPA",
            1 << 8: "HSPA",
            1 << 9: "HSPA+",
            1 << 10: "1XRTT",
            1 << 11: "EVDO0",
            1 << 12: "EVDOA",
            1 << 13: "EVDOB",
            1 << 14: "LTE",
            1 << 15: "5GNR",
            1 << 16: "LTE Cat-M",
            1 << 17: "LTE NB-IoT"
        }

        # Extract the technologies from the bitmask
        technologies = [name for bit, name in access_tech_map.items() if bitmask & bit]

        return technologies

    def _get_modem_property_as_string(self, property_name: str) -> str:
        """
        Helper method to retrieve a modem property as a string.

        Args:
        property_name (str): The name of the property to retrieve.

        Returns:
        str: The property value as a string.
        """
        assert self.modem_if is not None, "Modem object is not initialized"
        value = self.modem_if.Get(MM_MODEM_IF, property_name, dbus_interface=DBUS_PROPERTIES_IF)
        return str(value)

    def _get_access_tech_by_index(self, index: int) -> str | None:
        """
        Helper method to retrieve the access technology string by index.

        Args:
        index (int): The index of the access technology to retrieve.

        Returns:
        str | None: The access technology string if available, otherwise None.
        """
        assert self.modem_if is not None, "Modem object is not initialized"
        bitmask = self.modem_if.Get(MM_MODEM_IF, "AccessTechnologies", dbus_interface=DBUS_PROPERTIES_IF)
        assert bitmask is not None, "AccessTechnologies bitmask is None"
        techs_strs = Modem.access_tech_to_strings(int(bitmask))
        if len(techs_strs) > index:
            return techs_strs[index].lower()
        return None


class Bearer():
    def __init__(self, id):
        self.id = id
        self.bearer_if = self._get_bearer_by_id()

    def uptime(self):
        assert self.bearer_if is not None, "Bearer interface is not initialized"
        stats_properties = self.bearer_if.Get(MM_BEARER_IF, "Stats", dbus_interface=DBUS_PROPERTIES_IF)
        assert stats_properties is not None
        uptime = int(stats_properties.get("duration"))
        return uptime

    def ip(self):
        assert self.bearer_if is not None, "Bearer interface is not initialized"
        ipv4_properties = self.bearer_if.Get(MM_BEARER_IF, "Ip4Config", dbus_interface=DBUS_PROPERTIES_IF)
        assert ipv4_properties is not None
        ipv4_addr = str(ipv4_properties.get("address"))
        return ipv4_addr

    def _get_bearer_by_id(self):
        try:
            bearer_path = f'/org/freedesktop/ModemManager1/Bearer/{self.id}'
            bearer_obj = dbus.SystemBus().get_object(MM_DBUS_IF, bearer_path)
            bearer_interface = dbus.Interface(bearer_obj, MM_BEARER_IF)
            return bearer_interface
        except dbus.DBusException as e:
            logger.error(f"failed to get bearers interface: {e}")
            return None


class SIM():
    def __init__(self, id):
        self.id = id
        self.sim_if = self._get_sim_by_id()

    def imsi(self):
        assert self.sim_if is not None, "SIM interface is not initialized"
        imsi = self.sim_if.Get(MM_SIM_IF, "Imsi", dbus_interface=DBUS_PROPERTIES_IF)
        return str(imsi)

    def iccid(self):
        assert self.sim_if is not None, "SIM interface is not initialized"
        iccid = self.sim_if.Get(MM_SIM_IF, "SimIdentifier", dbus_interface=DBUS_PROPERTIES_IF)
        return str(iccid)

    def _get_sim_by_id(self):
        try:
            sim_path = f'/org/freedesktop/ModemManager1/SIM/{self.id}'
            sim_obj = dbus.SystemBus().get_object(MM_DBUS_IF, sim_path)
            sim_interface = dbus.Interface(sim_obj, MM_SIM_IF)
            return sim_interface
        except dbus.DBusException as e:
            logger.error(f"failed to get SIM interface: {e}")
            return None
