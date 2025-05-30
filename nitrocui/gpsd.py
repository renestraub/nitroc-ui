"""
gpsd wrapper

runs thread to receive JSON data from gpsd and store in queue
use .next() to get gpsd message
"""
import json  # or `import simplejson as json` if on Python < 2.6
import logging
import queue
import socket
import threading

logger = logging.getLogger('nitroc-ui')


class Gpsd(threading.Thread):
    GPSD_DATA_SOCKET = ('127.0.0.1', 2947)

    def __init__(self):
        super().__init__()

        self.connection_attemps = 0
        self.connect_msg = '?WATCH={"enable":true,"json":true}'.encode()
        self.response_queue = queue.Queue()
        self.thread_ready_event = threading.Event()
        self.thread_stop_event = threading.Event()
        self.daemon = True

    def setup(self):
        try:
            self.connection_attemps += 1

            if self.connection_attemps == 1:
                logger.info('connecting to gpsd')

            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listen_sock.connect(self.GPSD_DATA_SOCKET)  # raises socket.error if gpsd is not running

            # Start worker thread in daemon mode, will invoke run() method
            self.start()

            # Wait for worker thread to become ready.
            # Without this wait we might send the command before the thread can
            # handle the response.
            logger.debug('waiting for receive thread to become active')
            self.thread_ready_event.wait()

            logger.info('connected to gpsd')
            return True

        except socket.error as msg:
            if self.connection_attemps == 1:
                logger.warning(msg)
            return False

    def cleanup(self):
        if self.is_alive():
            logger.debug('requesting thread to stop')
            self.thread_stop_event.set()

            # Wait until thread ended
            self.join(timeout=1.0)
            logger.debug('thread stopped')

            # Close socket
            assert self.listen_sock
            self.listen_sock.close()
            self.listen_sock = None

    def next(self, timeout=5.0):
        # logger.debug(f'waiting {timeout}s for reponse from listener thread')
        try:
            response = self.response_queue.get(True, timeout)
            # logger.debug(f'got response {response}')
            return response
        except queue.Empty:
            logger.warning('timeout...')

    def run(self):
        """
        Thread running method

        - receives raw data from gpsd
        - parses ubx frames, decodes them
        - if a frame is received it is put in the receive queue
        """
        try:
            logger.debug('starting raw listener on gpsd')
            assert self.listen_sock
            self.listen_sock.send(self.connect_msg)
            self.listen_sock.settimeout(0.25)

            logger.debug('receiver ready')
            self.thread_ready_event.set()

            while not self.thread_stop_event.is_set():
                try:
                    data = self.listen_sock.recv(8192)
                    if data:
                        try:
                            json_strings = data.decode()
                            for s in json_strings.splitlines():
                                obj = json.loads(s)     # obj = dict of json
                                self.response_queue.put(obj)
                        except json.JSONDecodeError:
                            logger.warning('could not decode JSON data from gpsd, discarding')

                except socket.timeout:
                    pass

        except socket.error as msg:
            logger.error(msg)

        logger.debug('receiver done')
