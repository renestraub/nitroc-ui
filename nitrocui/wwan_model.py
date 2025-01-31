import logging
import threading
import time

from ping3 import ping

from .tools import is_valid_ipv4

logger = logging.getLogger('nitroc-ui')


# PING_HOST = '1.1.1.1'
PING_HOST = '46.231.204.136'    # netmodule.com


class Wwan(object):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert Wwan.instance is None
        Wwan.instance = self

        self.model = model
        self.wwan_thread = GsmWorker(self.model)

    def setup(self):
        self.wwan_thread.setup()


class GsmWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.state = 'init'
        self.counter = 0

    def setup(self):
        self.daemon = True
        self.name = 'wwan-worker'
        self.start()

    def run(self):
        logger.info("running wwan thread")
        self.state = 'init'
        self.counter = 0
        link_data = dict()

        while True:
            if self.state == 'init':
                if self._have_bearer():
                    logger.info('bearer found')

                    self.state = 'connected'

            elif self.state == 'connected':
                if not self._have_bearer():
                    logger.warning('lost IP connection')

                    link_data['delay'] = 0.0
                    self.model.publish('link', link_data)

                    self.state = 'init'
                else:
                    if self.counter % 5 == 2:
                        try:
                            delay = ping(PING_HOST, timeout=1.0)
                            if delay:
                                link_data['delay'] = round(float(delay), 3)
                            else:
                                link_data['delay'] = 0.0

                            self.model.publish('link', link_data)

                        except OSError as e:
                            logger.warning('Captured ping error')
                            logger.warning(e)

                            link_data['delay'] = 0.0
                            self.model.publish('link', link_data)
                            # self.state = 'init'

            self.counter += 1
            time.sleep(1.0)

    def _have_bearer(self):
        info = self.model.get('modem')
        if info and 'bearer-id' in info and 'bearer-ip' in info:
            bearer_ip = info['bearer-ip']
            if is_valid_ipv4(bearer_ip):
                return True
