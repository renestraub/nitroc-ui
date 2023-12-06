# import logging
import threading
import time


class TransmitQueue():
    """
    Transmit queue

    - Thread safe
    - Size limited
    - Stores data with timestamp in a map as follows
      {"time": <time>, "data": <data>}
    """
    def __init__(self, max_queue_size):
        super().__init__()

        assert 1 <= max_queue_size < 3000
        self._max_queue_size = max_queue_size
        self._lock = threading.Lock()
        self._data_queue = list()

    def num_entries(self):
        with self._lock:
            return len(self._data_queue)

    def all_entries(self):
        with self._lock:
            return self._data_queue

    def first_entries(self, num):
        """
        Gets first <num> entries

        If <num> exceeds the number of entries in the queue, all entries
        are returned without failing.
        """
        with self._lock:
            max = len(self._data_queue)
            if num > max:
                num = max
            # self._deqeue_head(num)
            return self._data_queue[:num]

    def remove_first(self, num):
        """
        Removes first <num> entries from queue

        If <num> is greater than queue size, removes all entries without
        failing.
        """
        with self._lock:
            # assert num <= len(self._data_queue)
            max = len(self._data_queue)
            if num > max:
                num = max
            # self._deqeue_head(num)
            self._data_queue = self._data_queue[num:]

    def add(self, data):
        """
        Adds entry to transmit queue

        Removes oldest entry to make space for new one if queue size limit
        is reached.
        """
        now = time.time()
        now_ms = int(1000.0 * now)
        data_set = {"time": now_ms, "data": data}

        with self._lock:
            num_entries = len(self._data_queue)
            # logger.debug(f'num q entries {num_entries}')
            if num_entries >= self._max_queue_size:
                # logger.info('queue overflow, dropping old elements')
                self._data_queue = self._data_queue[1:]

            self._data_queue.append(data_set)

    def _deqeue_head(self, amount):
        data = self._data_queue[0:amount]
        self._data_queue = self._data_queue[amount:]
        return data
