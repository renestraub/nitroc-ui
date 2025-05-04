"""
Minimal Web UI for NITROC

Uses Tornado webserver
"""

import json
import logging
import os
# import sys

import requests
import threading
import time
import tornado.ioloop
import tornado.web
import tornado.websocket

from ._version import __version__ as version
from .data_model import Model
from .wwan_model import Wwan
# from .gnss_model import Gnss
from .gnss_pos import GnssPosition
from .mm import MM
from .pagegnss import GnssHandler, GnssSaveStateHandler, GnssClearStateHandler
from .pagegnss import GnssFactoryResetHandler, GnssColdStartHandler

from .pagegnssedit import GnssEditHandler, GnssSaveHandler, GnssRestartHandler
from .realtime import RealtimeHandler, RealtimeWebSocket
from .pageinfo import MainHandler
from .pagetraffic import TrafficHandler, TrafficImageHandler
from .things import Things, RpcRunner


FORMAT = '%(asctime)-15s %(levelname)-8s %(module)-12s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('nitroc-ui')
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)


# Init section
logger.info(f'welcome to NITROC-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
logger.info(f'running server from {module_path}')


class ModemResetHandler(tornado.web.RequestHandler):
    def get(self):
        imei = self.get_query_argument('imei')
        if imei:
            logger.warning(f'resetting modem with IMEI {imei}')
            m = MM.modem(imei)
            if m:
                m.reset()
                self.write('Modem reset successfully')
            else:
                self.write('No modem found')
        else:
            self.write('No IMEI specified')


class SystemSleepHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('putting system to sleep')
        self.write('Initiated system sleep procedure')
        os.system("rtcwake -s 300 -m off")


class SystemRebootHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('rebooting system')
        self.write('Initiated system reboot')
        os.system("reboot")


class SystemPowerdownHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('powering down system')
        self.write('Initiated system power down')
        os.system("poweroff")


class CloudHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('starting/stopping cloud logging service')
        enable = self.get_query_argument('enable', 'False')

        things = Things.instance
        assert things
        res = things.enable(enable == 'True')
        self.write(res)


class GsmCellLocateHandler(tornado.web.RequestHandler):
    def get(self):
        mcc = self.get_query_argument('mcc', '0')
        mnc = self.get_query_argument('mnc', '0')
        lac = self.get_query_argument('lac', '0')
        tac = self.get_query_argument('tac', '0')
        cid = self.get_query_argument('cid', '0')

        logger.info(f'cellinfo: mcc {mcc}, mnc {mnc}, lac {lac}, tac {tac}, cid {cid}')

        # try to find cell location with opencellid
        # request form = https://opencellid.org/ajax/searchCell.php?mcc=228&mnc=1&lac=3434&cell_id=17538051

        # opencellid API expects LAC, for 4G/LTE this is the TAC
        if lac == '0':
            lac = tac
        args = {'mcc': mcc, 'mnc': mnc, 'lac': lac, 'cell_id': cid}
        r = requests.get("https://opencellid.org/ajax/searchCell.php", params=args)

        # Blindly try to convert to JSON, check for errors later
        d = json.loads(r.text)
        if isinstance(d, dict) and "lon" in d and "lat" in d:
            lon = d["lon"]
            lat = d["lat"]
            logger.info(f'cell location: {lon}/{lat}')

            result = f'Cell Location: {lon}/{lat}'

            # try to determine location for lon/lat with OSM reverse search
            """
            GET /reverse.php?lat=47.321486&lon=7.964929&zoom=18&format=jsonv2 HTTP/2
            User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0
            Cookie: _osm_totp_token=790611
            """

            # URL for reverse geocoding
            url = "https://nominatim.openstreetmap.org/reverse.php"
            # Query parameters
            params = {
                "lat": lat,
                "lon": lon,
                "zoom": 16,
                "format": "jsonv2"
            }
            # Headers (to avoid being blocked)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0"
            }

            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "display_name" in data:
                    location_name = data["display_name"]
                    logger.info(f"location name: {location_name}")
                    result += '</br>'
                    result += f'{location_name}'
                else:
                    logger.info("Location name not found in the response.")
            else:
                logger.info(f"Failed to fetch location. HTTP Status Code: {response.status_code}")

            result += '</br>'
            result += f'<a target="_blank" href="http://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16">Link To OpenStreetMap</a>'
        else:
            result = 'Cell not found in opencellid database'

        self.write(result)


class NotImplementedHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('WARNING: Function not yet implemented')


class RpcReboot(RpcRunner):
    def run(self, _args: str) -> bool:
        logger.warning('rebooting system in 5 seconds')
        threading.Thread(target=RpcReboot.do_reboot).start()
        return True

    @staticmethod
    def do_reboot():
        time.sleep(5)
        logger.warning('rebooting system now')
        os.system("reboot")


class RpcPoweroff(RpcRunner):
    def run(self, _args: str) -> bool:
        logger.warning('powering down system in 5 seconds')
        threading.Thread(target=RpcPoweroff.do_poweroff).start()
        return True

    @staticmethod
    def do_poweroff():
        time.sleep(5)
        logger.warning('powering off system now')
        os.system("poweroff")


class RpcLED(RpcRunner):
    def __init__(self, method, model):
        super().__init__(method)
        self.model = model

    def run(self, args: str) -> bool:
        COLORS = {"off", "red", "green", "blue", "white"}
        if args in COLORS:
            self.model.indicator(args)
            return True
        else:
            return False


def run_server(port=80):
    model = Model()
    model.setup()

    wwan = Wwan(model)
    wwan.setup()

    # gnss = Gnss(model)
    # gnss.setup()

    gnss_pos = GnssPosition(model)
    gnss_pos.setup()

    things = Things(model)
    things.setup()
    things.register_rpc(RpcReboot("reboot"))
    things.register_rpc(RpcPoweroff("poweroff"))
    things.register_rpc(RpcLED("led", model))

    # Start cloud logging by default
    things.enable(True)

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static")
    }

    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/gnss", GnssHandler),
        (r"/gnss_edit", GnssEditHandler),
        (r"/realtime", RealtimeHandler),
        (r"/traffic", TrafficHandler),
        (r'/traffic/img/(?P<filename>.+\.png)?', TrafficImageHandler),

        (r"/do_cell_locate", GsmCellLocateHandler),
        (r"/do_cloud", CloudHandler),
        (r"/do_gnss_save", GnssSaveHandler),
        (r"/do_gnss_restart", GnssRestartHandler),
        (r"/do_modem_reset", ModemResetHandler),
        (r"/do_system_sleep", SystemSleepHandler),
        (r"/do_system_reboot", SystemRebootHandler),
        (r"/do_system_powerdown", SystemPowerdownHandler),

        (r"/do_ser2net", NotImplementedHandler),
        (r"/do_gnss_state_save", GnssSaveStateHandler),
        (r"/do_gnss_state_clear", GnssClearStateHandler),
        (r"/do_gnss_factory_reset", GnssFactoryResetHandler),
        (r"/do_gnss_coldstart", GnssColdStartHandler),

        (r"/ws_realtime", RealtimeWebSocket),
    ], **settings) # type: ignore

    # logging.getLogger("tornado.access").setLevel(logging.DEBUG)
    # logging.getLogger("tornado.application").setLevel(logging.DEBUG)
    # logging.getLogger("tornado.general").setLevel(logging.DEBUG)

    try:
        app.listen(port)
    except OSError:
        logger.warning(f'server port {port} in use. Is another webserver running?')

    tornado.ioloop.IOLoop.current().start()


# Can be invoked with python3 -m nitrocui.server
if __name__ == "__main__":
    run_server()
