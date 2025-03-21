"""
Realtime Display Page

Display speed, gnss fix & esf status and mobile link information
using a websocket
"""
import logging

from typing import TypeVar, cast

import tornado.web
import tornado.websocket

from ._version import __version__ as version
from .data_model import Model
from .tools import format_size

logger = logging.getLogger('nitroc-ui')


T = TypeVar("T")

class Data():
    def __init__(self, data):
        super().__init__()
        self._data = data

    def get(self, default: T, *keys) -> T:
        dct = self._data
        for key in keys:
            try:
                dct = dct[key]
            except KeyError as e:
                logger.debug(f'cannot get {e}')
                return default
        return cast(T, dct)


class RealtimeHandler(tornado.web.RequestHandler):
    def get(self):
        m = Model.instance
        assert m
        md = m.get_all()
        serial = md['sys-version']['serial']

        self.render('realtime.html',
                    title=f'{serial}',
                    version=version
                    )


class RealtimeWebSocket(tornado.websocket.WebSocketHandler):
    instance = None
    connections = set()
    counter = 0
    timer_fn = None
    esf_status = None

    def __init__(self, application, request, **kwargs):
        logger.info(f'new SimpleWebSocket {self}')
        super().__init__(application, request, **kwargs)

        if not RealtimeWebSocket.instance:
            RealtimeWebSocket.instance = self
            RealtimeWebSocket.counter = 0

            logger.info('starting websocket timer')
            RealtimeWebSocket.timer_fn = tornado.ioloop.PeriodicCallback(RealtimeWebSocket.timer, 900)
            RealtimeWebSocket.timer_fn.start()

    def open(self):
        logger.info(f'adding new connection {self}')
        RealtimeWebSocket.connections.add(self)

    def on_close(self):
        logger.info('closing connection')
        RealtimeWebSocket.connections.remove(self)

    @staticmethod
    def timer():
        m = Model.instance
        assert m
        md = m.get_all()
        d = Data(md)

        rx, tx = d.get((0, 0), 'net-wwan0', 'bytes')
        rx = format_size(int(rx))
        tx = format_size(int(tx))
        delay_in_ms = d.get(0.0, 'link', 'delay') * 1000.0
        sq = d.get(0, 'modem', 'signal-quality')
        rat = d.get('n/a', 'modem', 'access-tech')
        rat2 = d.get('n/a', 'modem', 'access-tech2')
        rat = f'{rat} {rat2}'
        wwan0 = {
            'rx': f'{rx}',
            'tx': f'{tx}',
            'latency': str(delay_in_ms),
            'signal': str(sq),
            'rat': rat
        }

        default = {'fix': '-', 'lon': 0.0, 'lat': 0.0, 'speed': 0.0, 'pdop': 99.99}
        pos = d.get(default, 'gnss-pos')

        # default_esf = {'esf-status': {'fusion': 'n/a', 'ins': 'n/a', 'imu': 'n/a', 'imu-align': 'n/a'}}
        # gnss_state = RealtimeWebSocket.safeget(default_esf, md, 'gnss-state')
        # esf_state = gnss_state['esf-status']

        # default = {'speed': 0.0, 'coolant-temp': 0.0}
        info = {
            'clients': len(RealtimeWebSocket.connections),
            'time': RealtimeWebSocket.counter,
            'pos': pos,
            # 'esf': esf_state,
            'wwan0': wwan0,
        }
        [client.write_message(info) for client in RealtimeWebSocket.connections]

        RealtimeWebSocket.counter += 1
