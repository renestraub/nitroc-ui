# import pytest

from nitrocui.transmit_queue import TransmitQueue


class TestTransmitQueueBasic:
    def test_empty(self):
        tq = TransmitQueue(3)
        assert tq.num_entries() == 0

    def test_add_num_entries(self):
        tq = TransmitQueue(3)
        tq.add(1)
        assert tq.num_entries() == 1
        tq.add(2)
        assert tq.num_entries() == 2
        tq.add(3)
        assert tq.num_entries() == 3

    def test_limit(self):
        tq = TransmitQueue(2)
        self._fill(tq, 3)
        assert tq.num_entries() == 2

        data = tq.all_entries()
        assert data[0]['data'] == 2
        assert data[1]['data'] == 3

        tq.add(4)
        assert tq.num_entries() == 2

        data = tq.all_entries()
        assert data[0]['data'] == 3
        assert data[1]['data'] == 4

    def test_get_all(self):
        tq = TransmitQueue(4)
        self._fill(tq, 4)

        data = tq.all_entries()
        assert tq.num_entries() == 4
        assert data[0]['data'] == 1
        assert data[1]['data'] == 2
        assert data[2]['data'] == 3
        assert data[3]['data'] == 4

    def test_first(self):
        tq = TransmitQueue(4)
        self._fill(tq, 4)

        data = tq.first_entries(2)
        assert data[0]['data'] == 1
        assert data[1]['data'] == 2

    def test_get_more_than_exist(self):
        tq = TransmitQueue(2)
        self._fill(tq, 2)

        data = tq.first_entries(3)
        print(data)
        assert len(data) == 2
        assert data[0]['data'] == 1
        assert data[1]['data'] == 2

    def test_remove_first(self):
        tq = TransmitQueue(4)
        self._fill(tq, 4)

        tq.remove_first(2)
        data = tq.all_entries()
        assert data[0]['data'] == 3
        assert data[1]['data'] == 4

    def test_remove_more_than_present(self):
        tq = TransmitQueue(4)
        self._fill(tq, 2)

        tq.remove_first(3)
        assert tq.num_entries() == 0

        tq.remove_first(99)
        assert tq.num_entries() == 0

    @staticmethod
    def _fill(tq, num):
        for i in range(1, num + 1):
            tq.add(int(i))
