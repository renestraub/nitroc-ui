"""
Accessor to upload data to Thingsboard

Store your device token in /etc/thingsboard.conf

[API]
Server=name:port
Token=xyz
"""
import configparser
import json
import logging
import math
import threading
import time
from io import BytesIO

import pycurl

from nitrocui.transmit_queue import TransmitQueue
from nitrocui._version import __version__ as ui_version

logger = logging.getLogger('vcu-ui')


class Things(threading.Thread):
    # Singleton accessor
    instance = None

    # Upload every 30 seconds
    TELEMETRY_UPLOAD_PERIOD = 30

    # Upload at most 120 entries. Assuming around 100 bytes per entry,
    # this makes 12 kBytes.
    TELEMETRY_MAX_ITEMS_TO_UPLOAD = 120

    # New entries are dropped when this size is reached
    # Assumption is that this queue size is good for 10 minutes
    MAX_QUEUE_SIZE = 600

    def __init__(self, model):
        super().__init__()

        assert Things.instance is None
        Things.instance = self

        self.model = model
        self.state = 'init'
        self.active = False

        self.config = configparser.ConfigParser()
        try:
            self.config.read('/etc/thingsboard.conf')
            self.api_server = self.config.get('API', 'Server')
            self.api_token = self.config.get('API', 'Token')
            self.has_server = True
        except configparser.Error as e:
            logger.warning('ERROR: Cannot get Thingsboard config')
            logger.info(e)
            self.has_server = False

        self._attributes_queue = TransmitQueue(1)
        self._data_queue = TransmitQueue(self.MAX_QUEUE_SIZE)
        self._data_collector = ThingsDataCollector(model, self._data_queue, self._attributes_queue)

    def setup(self):
        self.daemon = True
        if self.has_server:
            self.start()

    def enable(self, enable):
        if enable:
            if self.has_server:
                if not self.active:
                    logger.info("service starting")
                    self._data_collector.enable()
                    self.active = True
                    self.state = 'init'
                    res = 'Started cloud logger'
                else:
                    res = 'Cloud logger already running'
            else:
                res = 'Cannot start. No configuration present'
        else:
            logger.info("service stopping")
            if self.active:
                self._data_collector.disable()
                self.active = False
                res = 'Stopped cloud logger'
            else:
                res = 'Cloud logger not running'

        self.model.publish('cloud', self.active)

        return res

    def run(self):
        cnt = 0

        while True:
            if self.active:
                next_state = self.state
                md = self.model.get_all()

                if self.state != 'connected':
                    # Check if we are connected
                    if 'modem' in md:
                        m = md['modem']
                        if 'modem-id' in m:
                            if 'bearer-id' in m:
                                # logger.info('link ready, changing to connected state')
                                cnt = 0
                                next_state = 'connected'

                elif self.state == 'connected':
                    # Upload any pending data
                    self._upload_attributes()

                    if cnt % Things.TELEMETRY_UPLOAD_PERIOD == 5:
                        self._upload_telemetry()

                    # TODO: check for error and switch to disconnected state in case of problem

                # state change
                if self.state != next_state:
                    logger.info(f'changed state from {self.state} to {next_state}')
                    self.state = next_state

                cnt += 1

            time.sleep(1.0)

    def _upload_telemetry(self):
        """
        Sends telemtry data

        Checks for entries in _data_queue If entries are present, gets up to
        TELEMETRY_MAX_ITEMS_TO_UPLOAD entries and tries to upload them. If upload is ok,
        removes entries from queue. Otherwise leaves entries for next try.
        """

        # Are there any entries at all?
        queue_entries = self._data_queue.num_entries()
        if queue_entries >= 1:
            # On every upload report current queue size
            data = {'tb-qsize': queue_entries}
            self._data_queue.add(data)

            # Build HTTP query string with queue data
            entries = self._data_queue.first_entries(Things.TELEMETRY_MAX_ITEMS_TO_UPLOAD)
            num_entries = len(entries)
            assert len(entries) >= 0

            post_data = list()
            for entry in entries:
                data = {'ts': entry['time'], 'values': entry['data']}
                post_data.append(data)

            # Upload the collected data
            res = self._post_data('telemetry', post_data)
            if res:
                # Transmission was ok, remove data from queue
                self._data_queue.remove_first(num_entries)
                logger.debug(f'removing {num_entries} entries from queue')
            else:
                logger.warning('could not upload telemetry data, keeping in queue')
                logger.warning(f'{queue_entries} entries in queue')

    def _upload_attributes(self):
        """
        Upload a single attribute entry.

        Assumes all attributes are in one entry
        TODO: Rework to allow more than one entry, combine code with _upload_telemetry
        """
        if self._attributes_queue.num_entries() >= 1:
            entry = self._attributes_queue.all_entries()[0]
            post_data = entry['data']

            res = self._post_data('attributes', post_data)
            if res:
                # Transmission was ok, remove data from queue
                self._attributes_queue.remove_first(1)
            else:
                logger.warning('could not upload attribute data, keeping in queue')

    def _post_data(self, msgtype, payload):
        """
        Sends data with HTTP(S) POST request to Thingsboard server

        Captures pycurl exceptions and checks for 200 (OK) response
        from server.

        TODO:
        Check timeout behavior. While we are transmitting data is not captured and can get lost!
        Ideally this method would run in it's own thread with transmit queue
        """
        res = False

        assert msgtype == 'attributes' or msgtype == 'telemetry'

        c = pycurl.Curl()
        c.setopt(pycurl.URL, f'{self.api_server}/api/v1/{self.api_token}/{msgtype}')
        c.setopt(pycurl.HTTPHEADER, ['Content-Type:application/json'])
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.CONNECTTIMEOUT_MS, 3000)
        c.setopt(pycurl.TIMEOUT_MS, 4000)
        # c.setopt(c.VERBOSE, True)

        body_as_json_string = json.dumps(payload)  # dict to json
        body_as_json_bytes = body_as_json_string.encode()
        body_as_file_object = BytesIO(body_as_json_bytes)

        # prepare and send. See also: pycurl.READFUNCTION to pass function instead
        c.setopt(pycurl.READDATA, body_as_file_object)
        c.setopt(pycurl.POSTFIELDSIZE, len(body_as_json_string))

        try:
            info = dict()
            info['state'] = 'sending'
            self.model.publish('things', info)

            c.perform()
            bytes_sent = len(body_as_json_bytes)
            logger.debug(f'sent {bytes_sent} bytes to {self.api_server}')

            info['state'] = 'sent'
            info['bytes'] = bytes_sent
            self.model.publish('things', info)

            response = int(c.getinfo(pycurl.RESPONSE_CODE))
            logger.debug(f'got response {response} from server')

            if response == 200:
                bytes_sent = int(c.getinfo(pycurl.CONTENT_LENGTH_UPLOAD))
                logger.debug(f'{bytes_sent} bytes uploaded')

                res = True
            else:
                logger.warning(f'bad HTTP response {response} received')

        except pycurl.error as e:
            logger.warning("failed uploading data to Thingsboard")
            logger.warning(e)
        finally:
            c.close()

        return res


class ThingsDataCollector(threading.Thread):
    # Check/Upload every 120 seconds
    ATTRIBUTE_CHECKING_PERIOD = 120

    # Suppress GNSS update if movement less than this distance in meter
    GNSS_UPDATE_DISTANCE = 1.5

    def __init__(self, model, data_queue, attributes_queue):
        super().__init__()

        self.model = model
        self.active = False
        self._data_queue = data_queue
        self._attributes_queue = attributes_queue

        self.lat_last_rad = 0
        self.lon_last_rad = 0
        self.obd2_last_speed = -1
        self.rat_last = None
        self.rat2_last = None

        self.daemon = True
        self.start()

    def enable(self):
        self.active = True

    def disable(self):
        self.active = False

    def run(self):
        logger.info("starting cloud data collector thread")

        cnt = 0
        while True:
            if self.active:
                md = self.model.get_all()

                # Attributes
                if cnt % self.ATTRIBUTE_CHECKING_PERIOD == 0:
                    self._attributes(md)

                # Less important live information
                if cnt % 10 == 0:
                    self._info(md)

                # Traffic information every two minutes
                if cnt % 120 == 0:
                    self._traffic(md)

                # Force GNSS update once a minute, even if not moving
                force_update = (cnt % 60) == 0
                self._gnss(md, force_update)

                # OBD2 information every second, force update even when no change
                force_update = (cnt % 60) == 0
                self._obd2(md, force_update)

                cnt += 1

            time.sleep(1.0)

    def _attributes(self, md):
        os_version = md['sys-version']['sys']
        serial = md['sys-version']['serial']
        hw_ver = md['sys-version']['hw']
        bootloader_ver = md['sys-version']['bl']
        uptime = md['sys-datetime']['uptime']
        attrs = {
            "serial": serial,
            "os-version": os_version,
            "ui-version": ui_version,
            "bootloader-version": bootloader_ver,
            "hardware": hw_ver,
            "uptime": uptime
        }

        if 'sys-boot' in md:
            reason = md['sys-boot']['reason']
            attrs['start-reason'] = reason

        if 'gnss' in md:
            info = md['gnss']
            attrs['gnss-fw-version'] = info['fwVersion']
            attrs['gnss-protocol'] = info['protocol']

        if 'ubxlib' in md:
            info = md['ubxlib']
            attrs['ubxlib-version'] = info['version']

        if 'modem' in md:
            info = md['modem']

            if 'revision' in info:
                attrs['wwan-version'] = info['revision']

            if 'sim-id' in info:
                imsi = info['sim-imsi']
                attrs['sim-imsi'] = imsi
                iccid = info['sim-iccid']
                attrs['sim-iccid'] = iccid

        self._attributes_queue.add(attrs)

    def _info(self, md):
        telemetry = dict()
        if 'sys-misc' in md:
            info = md['sys-misc']
            telemetry['temperature'] = info['temp']
            telemetry['cpu-load'] = info['load'][0]
            telemetry['voltage-in'] = info['v_in']
            telemetry['mem-free'] = info['mem'][1]
            if 'temp_mb' in info:
                telemetry['temperature-board'] = info['temp_mb']

        if 'link' in md:
            info = md['link']
            if 'delay' in info:
                delay_in_ms = info['delay'] * 1000.0
                telemetry['wwan-delay'] = f'{delay_in_ms:.0f}'

        if 'modem' in md:
            info = md['modem']

            if 'access-tech' in info:
                rat = info['access-tech']
                # print(f'rat: {rat}')
                if rat:  # and rat != self.rat_last:
                    self.rat_last = rat
                    # print(ThingsDataCollector.rat_to_number(rat))
                    telemetry['rat'] = ThingsDataCollector.rat_to_number(rat)

            if 'access-tech2' in info:
                rat = info['access-tech2']
                # print(f'rat2: {rat}')
                if rat:  # and rat != self.rat2_last:
                    self.rat2_last = rat
                    # print(ThingsDataCollector.rat_to_number(rat))
                    telemetry['rat2'] = ThingsDataCollector.rat_to_number(rat)

            if 'signal-quality' in info:
                sq = info['signal-quality']
                telemetry['siqnal-qlt'] = sq

            if 'signal-quality2' in info:
                sq = info['signal-quality2']
                telemetry['signal-qlt-ext'] = sq

            if 'bearer-id' in info:
                id = info['bearer-id']
                telemetry['bearer-id'] = id
                if 'bearer-uptime' in info:
                    uptime = info['bearer-uptime']
                    telemetry['bearer-uptime'] = uptime

        if 'net-wwan0' in md:
            info = md['net-wwan0']
            (rx, tx) = info['bytes']
            telemetry['wwan0-rx'] = f'{rx}'
            telemetry['wwan0-tx'] = f'{tx}'

        if 'net-wlan0' in md:
            info = md['net-wlan0']
            (rx, tx) = info['bytes']
            telemetry['wlan0-rx'] = f'{rx}'
            telemetry['wlan0-tx'] = f'{tx}'

        if 'phy-broadr0' in md:
            info = md['phy-broadr0']
            quality = info['quality']
            telemetry['broadr0-quality'] = f'{quality}'

        if len(telemetry) > 0:
            self._data_queue.add(telemetry)

    def _traffic(self, md):
        telemetry = dict()
        if 'traffic-wwan0' in md:
            info = md['traffic-wwan0']
            telemetry['wwan0-rx-day'] = f'{info["day_rx"]}'
            telemetry['wwan0-tx-day'] = f'{info["day_tx"]}'
            telemetry['wwan0-rx-month'] = f'{info["month_rx"]}'
            telemetry['wwan0-tx-month'] = f'{info["month_tx"]}'

        if len(telemetry) > 0:
            self._data_queue.add(telemetry)

    def _gnss(self, md, force):
        if 'gnss-pos' in md:
            pos = md['gnss-pos']
            if 'lon' in pos and 'lat' in pos:
                lon_rad = math.radians(pos['lon'])
                lat_rad = math.radians(pos['lat'])

                d = self._distance(lon_rad, lat_rad)
                if force or d > self.GNSS_UPDATE_DISTANCE:
                    self._data_queue.add(pos)

                    self.lat_last_rad = lat_rad
                    self.lon_last_rad = lon_rad

    def _distance(self, lon_rad, lat_rad):
        R = 6371.0e3
        d_lat_rad = self.lat_last_rad - lat_rad
        d_lon_rad = self.lon_last_rad - lon_rad

        a = math.sin(d_lat_rad / 2) * math.sin(d_lat_rad / 2) + \
            math.cos(lat_rad) * math.cos(self.lat_last_rad) * \
            math.sin(d_lon_rad / 2) * math.sin(d_lon_rad / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        d = R * c

        return d

    def _obd2(self, md, force):
        if 'obd2' in md:
            info = md['obd2']
            speed = info['speed']
            speed_diff = speed - self.obd2_last_speed
            # print(f'TB telemetry {speed} {self.obd2_last_speed}')
            if force or abs(speed_diff) >= 1.0:
                data = {
                    'obd2-speed': f'{speed}',
                }
                self._data_queue.add(data)

                self.obd2_last_speed = speed

    @staticmethod
    def rat_to_number(rat_str):
        if 'lte' in rat_str:
            return 4
        elif 'umts' in rat_str:
            return 3
        elif 'gsm' in rat_str:
            return 2
        else:
            return 0
