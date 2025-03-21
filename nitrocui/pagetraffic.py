"""
Traffic Page
"""
import logging
import subprocess

import tornado.web

from ._version import __version__ as version
from .data_model import Model
from .tools import format_size

logger = logging.getLogger('nitroc-ui')


class TE(object):
    def __init__(self, header, text):
        self.header = header
        self.text = text


class TrafficHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            tes = list()
            data = dict()

            # General System Information
            m = Model.instance
            assert m
            md = m.get_all()

            serial = md['sys-version']['serial']

            if 'traffic-wwan0' in md:
                data['traffic-wwan0'] = 'true'
                info = md['traffic-wwan0']

                tes.append(TE('<b>wwan0</b>', ''))
                TrafficHandler.append(tes, 'Day', int(info['day_rx']), int(info['day_tx']))
                TrafficHandler.append(tes, 'Month', int(info['month_rx']), int(info['month_tx']))
                TrafficHandler.append(tes, 'Year', int(info['year_rx']), int(info['year_tx']))
            else:
                data['traffic-wwan0'] = 'false'

            self.render('traffic.html',
                        title=f'{serial}',
                        table=tes,
                        data=data,
                        version=version)

        except KeyError:
            self.render('traffic.html',
                        title='NITROC',
                        table=None,
                        data=None,
                        version='n/a')

    @staticmethod
    def append(tes, label, rx, tx):
        rx_str = format_size(rx)
        tx_str = format_size(tx)
        tot_str = format_size(rx + tx)
        tes.append(TE(label, f'Rx: {rx_str}<br>Tx: {tx_str}<br>Total: {tot_str}'))


class TrafficImageHandler(tornado.web.RequestHandler):
    image_options = {
        'daily.png': ['-d'],
        'monthly.png': ['-m'],
        'summary.png': ['-vs']
    }

    def get(self, filename):
        logger.info(f'asking for traffic image {filename}')
        try:
            vnstati_call = ['/usr/bin/vnstati', '-o', '-', '--noedge']
            vnstati_call += self.image_options[filename]
            logger.info(vnstati_call)

            cp = subprocess.run(vnstati_call, capture_output=True)
            if cp.returncode == 0:
                s = cp.stdout
                self.set_header('Content-type', 'image/jpeg')
                self.set_header('Content-length', len(s))
                self.write(s)

        except FileNotFoundError:
            logger.info('vnstati not found')
