"""
Realtime Display Page

Display speed, gnss fix & esf status and mobile link information
using a websocket
"""
import logging

import tornado.web
import tornado.websocket

from ._version import __version__ as version
from .data_model import Model
from .tools import format_size

logger = logging.getLogger('nitroc-ui')


class RealtimeHandler(tornado.web.RequestHandler):
    def get(self):
        m = Model.instance
        assert m
        md = m.get_all()
        serial = md.get('-', 'sys-version', 'serial')

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

        rx, tx = md.get((0, 0), 'net-wwan0', 'bytes')
        rx = format_size(int(rx))
        tx = format_size(int(tx))
        delay_in_ms = md.get(0.0, 'link', 'delay') * 1000.0
        sq = md.get(0, 'modem', 'signal-quality')
        rat = md.get('n/a', 'modem', 'access-tech')
        rat2 = md.get('n/a', 'modem', 'access-tech2')
        rat = f'{rat} {rat2}'
        wwan0 = {
            'rx': f'{rx}',
            'tx': f'{tx}',
            'latency': str(delay_in_ms),
            'signal': str(sq),
            'rat': rat
        }

        default = {'fix': '-', 'lon': 0.0, 'lat': 0.0, 'speed': 0.0, 'pdop': 99.99}
        pos = md.get(default, 'gnss-pos')

        info = {
            'clients': len(RealtimeWebSocket.connections),
            'time': RealtimeWebSocket.counter,
            'pos': pos,
            'wwan0': wwan0,
        }
        [client.write_message(info) for client in RealtimeWebSocket.connections]

        RealtimeWebSocket.counter += 1
