import logging
import threading
import time

from nitrocui.gpsd import Gpsd

logger = logging.getLogger('vcu-ui')


class GnssPosition(threading.Thread):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert GnssPosition.instance is None
        GnssPosition.instance = self

        self.model = model

        self.state = 'init'
        self.gps = None
        self.lon = 0
        self.lat = 0
        self.fix = 0
        self.speed = 0
        self.pdop = 0

    def setup(self):
        self.daemon = True
        self.name = 'gps-reader'
        self.start()

    def run(self):
        logger.info('running gps position thread')

        self.state = 'init'
        while True:
            # logger.info(f'gnss position thread: {self.state}')

            if self.state == 'init':
                self._state_init()
            elif self.state == 'connected':
                self._state_connected()
            elif self.state == 'timeout':
                self._state_timeout()
            else:
                time.sleep(0.8)

    def _state_init(self):
        logger.debug('trying to connect to gpsd')

        if not self.gps:
            self.gps = Gpsd()

        res = self.gps.setup()
        if res:
            logger.info('gpsd connected')
            self.state = 'connected'
        else:
            logger.warning('cannot connect to gpsd, is it running?')
            time.sleep(3.0)

    def _state_connected(self):
        try:
            report = self.gps.next()
            if report:
                self._handle_report(report)
            else:
                logger.warning('gpsd timeout, maybe connection is lost')
                self.state = 'timeout'
        except KeyError as e:
            # For whatever reasons getting GPS data from gps daemon is unstable.
            # Have to handle KeyErrors in order to keep system running.
            logger.warning('gps module KeyError')
            logger.warning(e)

    def _state_timeout(self):
        logger.warning('connection to gpsd lost')
        self.model.remove('gnss-pos')

        self.gps.cleanup()
        self.gps = None
        self.state = 'init'

    def _handle_report(self, report):
        if report['class'] == 'SKY':
            # Remember PDOP only, will be sent on next TPV message
            if 'pdop' in report:
                self.pdop = report['pdop']

        if report['class'] == 'TPV':
            fix = report['mode']
            if fix == 0 or fix == 1:
                self.fix = 'No Fix'
            elif fix == 2:
                self.fix = '2D'
            elif fix == 3:
                self.fix = '3D'

            if 'status' in report:
                status = report['status']
                if status == 2 and self.fix == '3D':
                    self.fix = '3D DGPS'

            if 'speed' in report:
                self.speed = report['speed']

            # Ensure we have lon/lat in report
            # only update when present, to avoid 0/0 position messages
            if 'lon' in report and 'lat' in report:
                self.lon = report['lon']
                self.lat = report['lat']

                pos = dict()
                pos['fix'] = self.fix
                pos['lon'] = self.lon
                pos['lat'] = self.lat
                pos['speed'] = self.speed
                pos['pdop'] = self.pdop

                self.model.publish('gnss-pos', pos)
