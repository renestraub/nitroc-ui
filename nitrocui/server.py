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
# from .gnss_pos import GnssPosition
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
logger.setLevel(logging.DEBUG)


# Init section
logger.info(f'welcome to NITROC-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
logger.info(f'running server from {module_path}')


class LocationHandler(tornado.web.RequestHandler):
    def get(self):
        m = MM.modem()
        if m:
            m.setup_location_query()
            self.write('3GPP location query enabled')
        else:
            self.write('No modem found')


class ModemResetHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('resetting modem')
        m = MM.modem()
        if m:
            m.reset()
            self.write('Modem reset successfully')
        else:
            self.write('No modem found')


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
        enable = self.get_query_argument('enable', False)

        things = Things.instance
        res = things.enable(enable == 'True')
        self.write(res)


class GsmCellLocateHandler(tornado.web.RequestHandler):
    def get(self):
        mcc = self.get_query_argument('mcc', 0)
        mnc = self.get_query_argument('mnc', 0)
        lac = self.get_query_argument('lac', 0)
        cid = self.get_query_argument('cid', 0)

        logger.debug(f'cellinfo: mcc {mcc}, mnc {mnc}, lac {lac}, cid {cid}')

        # https://opencellid.org/ajax/searchCell.php?mcc=228&mnc=1&lac=3434&cell_id=17538051
        args = {'mcc': mcc, 'mnc': mnc, 'lac': lac, 'cell_id': cid}
        r = requests.get("https://opencellid.org/ajax/searchCell.php", params=args)
        if r.text != "false":
            d = json.loads(r.text)
            lon = d["lon"]
            lat = d["lat"]

            result = f'Cell Location: {d["lon"]}/{d["lat"]}'

            # try to determine location for lon/lat with OSM reverse search
            args = {'lon': lon, 'lat': lat, 'format': 'json'}
            r = requests.get("https://nominatim.openstreetmap.org/reverse",
                             params=args)
            d = json.loads(r.text)
            if 'display_name' in d:
                location = d['display_name']

                result += '</br>'
                result += f'{location}'

            result += '</br>'
            result += f'<a target="_blank" href="http://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16">Link To OpenStreetMap</a>'

        else:
            result = 'Cell not found in opencellid database'

        self.write(result)


class NotImplementedHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('WARNING: Function not yet implemented')


class RpcReboot(RpcRunner):
    def run(self, _args: dict) -> bool:
        logger.warning('rebooting system in 5 seconds')
        thread = threading.Thread(target=RpcReboot.do_reboot)
        thread.start() 
        return True

    @staticmethod
    def do_reboot():
        time.sleep(5)
        logger.warning('rebooting system now')
        os.system("reboot")


class RpcLED(RpcRunner):
    def run(self, args: dict) -> bool:
        colors = {
            "off": "0 0 0",
            "red": "100 0 0",
            "green": "0 100 0",
            "blue": "0 0 100",
        }

        if args in colors:
            rgb_color = colors[args]
            logger.info(f"setting LED to {rgb_color}")

            rgb_path = r'/sys/class/leds/chromeos:multicolor:power/multi_intensity'
            with open(rgb_path, 'w') as f:
                f.write(rgb_color)

            brightness_path = r'/sys/class/leds/chromeos:multicolor:power/brightness'
            with open(brightness_path, 'w') as f:
                f.write("100")

            return True
        else:
            logger.info(f"unsupported color {args}")
            return False


def run_server(port=80):
    model = Model()
    model.setup()

    wwan = Wwan(model)
    wwan.setup()

    # gnss = Gnss(model)
    # gnss.setup()

    # gnss_pos = GnssPosition(model)
    # gnss_pos.setup()

    things = Things(model)
    things.setup()
    things.register_rpc(RpcReboot("reboot"))
    things.register_rpc(RpcLED("led"))

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

        (r"/do_location", LocationHandler),
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
    ], **settings)

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
