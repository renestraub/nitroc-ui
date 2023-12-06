"""
Traffic Page
"""
import logging
import subprocess

import tornado.web

from nitrocui._version import __version__ as version
from nitrocui.data_model import Model


CONFIG_FILE = '/etc/gnss/gnss0.conf'


logger = logging.getLogger('nitroc-ui')


class GnssEditHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            # General System Information
            m = Model.instance
            md = m.get_all()
            serial = md['sys-version']['serial']

            # Get GNSS config file
            try:
                with open(CONFIG_FILE) as f:
                    gnss_cfg = f.read()
            except FileNotFoundError:
                logger.warning(f'cannot find {CONFIG_FILE}')
                gnss_cfg = None

            self.render('gnss_edit.html',
                        title=f'{serial}',
                        data=gnss_cfg,
                        version=version)

        except KeyError:
            self.render('gnss_edit.html',
                        title='NITROC',
                        data=None,
                        version='n/a')


class GnssSaveHandler(tornado.web.RequestHandler):
    def post(self):
        logger.info('saving gnss config')
        gnss_cfg = self.get_argument('config', None)

        res = ''
        try:
            # TODO: Create backup file and save new config

            with open(CONFIG_FILE, 'w') as f:
                f.write(gnss_cfg)

            res = 'File succesfully written'
        except FileNotFoundError:
            logger.warning(f'cannot find {CONFIG_FILE}')
            res = 'Cannot write file'

        self.write(res)


class GnssRestartHandler(tornado.web.RequestHandler):
    def post(self):
        logger.info('restarting gnss handler')

        cp = subprocess.run(['/usr/bin/systemctl', 'restart', 'gnss-mgr'], stdout=subprocess.PIPE)
        rc = cp.returncode
        if rc == 0:
            res = 'gnss-mgr restarted succesfully'
        else:
            res = 'An error occured while restarting gnss-mgr'

        self.write(res)
