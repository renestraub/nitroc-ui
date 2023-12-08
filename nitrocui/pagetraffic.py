"""
Traffic Page
"""
import logging
import subprocess

import tornado.web

from ._version import __version__ as version
from .data_model import Model

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
            md = m.get_all()

            serial = md['sys-version']['serial']

            if 'traffic-wwan0' in md:
                data['traffic-wwan0'] = 'true'
                info = md['traffic-wwan0']

                tes.append(TE('<b>wwan0</b>', ''))

                rx = int(info['day_rx']) / 2**20
                tx = int(info['day_tx']) / 2**20
                tes.append(TE('Day', f'Rx: {rx:.2f} MiB<br>Tx: {tx:.2f} MiB<br>Total: {rx+tx:.2f} MiB'))

                rx = int(info['month_rx']) / 2**20
                tx = int(info['month_tx']) / 2**20
                tes.append(TE('Month', f'Rx: {rx:.1f} MiB<br>Tx: {tx:.1f} MiB<br>Total: {rx+tx:.2f} MiB'))

                rx = int(info['year_rx']) / 2**30
                tx = int(info['year_tx']) / 2**30
                tes.append(TE('Year', f'Rx: {rx:.2f} GiB<br>Tx: {tx:.2f} GiB<br>Total: {rx+tx:.2f} GiB'))
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
