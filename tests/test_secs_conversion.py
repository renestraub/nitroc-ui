# import pytest

from nitrocui.tools import secs_to_hhmm


class TestSecondsConversion:
    def test_one(self):
        h, m = secs_to_hhmm(0)
        assert h == 0
        assert m == 0

    def test_two(self):
        h, m = secs_to_hhmm(60)
        assert h == 0
        assert m == 1

    def test_3(self):
        h, m = secs_to_hhmm(121)
        assert h == 0
        assert m == 2

    def test_4(self):
        h, m = secs_to_hhmm(3600)
        assert h == 1
        assert m == 0

    def test_5(self):
        h, m = secs_to_hhmm(86400-31)
        assert h == 23
        assert m == 59

    def test_rounding_1(self):
        h, m = secs_to_hhmm(29)
        assert h == 0
        assert m == 0

    def test_rounding_2(self):
        h, m = secs_to_hhmm(30)
        assert h == 0
        assert m == 1
