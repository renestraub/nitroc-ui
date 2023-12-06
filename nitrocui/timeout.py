import time


class Timeout:
    def __init__(self, timeout_in_secs):
        """
        Creates a timeout object that starts right now.
        The timeout elapses after the specified number of seconds.

        :param timeout_in_secs: Seconds until timeout elapses. Must be > 0 and
        < MAX_ALLOWED_TIMEOUT
        """
        self.start_time = time.time()
        self.end_time = self.start_time + timeout_in_secs

    def has_elapsed(self):
        """
        Checks whether timeout has elapsed

        :return: True if timeout has elapsed, False otherwise
        """
        now = time.time()
        return now >= self.end_time

    def delta(self):
        """
        Return time since creation of object in seconds.

        :return: Delta time since object was created
        """
        delta = time.time() - self.start_time
        assert delta >= 0

        return delta
