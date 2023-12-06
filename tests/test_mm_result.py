import pytest

from nitrocui.mm import MmResult


class TestMmResult:
    def test_load_lines(self):
        mmr = MmResult(
            'modem-list.length   : 1\n'
            'modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/0')
        assert mmr._exists('modem-list.length')
        assert mmr._exists('modem-list.value[1]')

        mmr = MmResult('key : 1')
        assert mmr._exists('key')
        assert mmr.text('key') == '1'

        # FIXME: Should work as well
        # mmr = MmResult('key:1')
        # assert mmr._exists('key')
        # assert mmr.text('key') == '1'

    def test_empty_value(self):
        mmr = MmResult('key :')
        assert mmr._exists('key')
        assert mmr.text('key') is None

    def test_does_not_exist(self):
        mmr = MmResult('key : 123')
        res = mmr.text('key1')
        assert res is None

        res = mmr.dec('key2')
        assert res is None

        res = mmr.hex('key3')
        assert res is None

        res = mmr.number('key4')
        assert res is None

        res = mmr.id('key5')
        assert res is None

    def test_id(self):
        # No value
        mmr = MmResult('modem-list.value[1] :')
        assert mmr.id('modem-list.value[1]') is None

        # No index link
        # mmr = MmResult('modem-list.value[1] : 12345')
        # assert mmr.id('modem-list.value[1]') is None
        # FIXME: This one should fail

        # No ID
        mmr = MmResult('modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/')
        assert mmr.id('modem-list.value[1]') is None

        # No integer
        mmr = MmResult('modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/abc')
        assert mmr.id('modem-list.value[1]') is None

        # Ok
        mmr = MmResult('modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/1')
        assert mmr.id('modem-list.value[1]') == 1

    def test_text(self):
        # mmr = MmResult('key : any text')
        # assert mmr.text('key') == 'any text'
        # DODO: Should work as well

        mmr = MmResult('key : any_text')
        assert mmr.text('key') == 'any_text'

        mmr = MmResult('key : 12345')
        assert mmr.text('key') == '12345'

    def test_dec(self):
        mmr = MmResult('key : abcdef')
        assert mmr.dec('key') is None

        mmr = MmResult('key : 12345')
        assert mmr.dec('key') == 12345

        mmr = MmResult('key : -12345')
        assert mmr.dec('key') == -12345

    def test_hex(self):
        mmr = MmResult('key : gugus')
        assert mmr.hex('key') is None

        mmr = MmResult('key : -100')
        assert mmr.hex('key') == -256

        mmr = MmResult('key : 1234abcd')
        assert mmr.hex('key') == 0x1234abcd

    def test_number(self):
        mmr = MmResult('key : gugus')
        assert mmr.number('key') is None

        mmr = MmResult('key : 1.23456')
        assert mmr.number('key') == pytest.approx(1.23456)

        mmr = MmResult('key : -1.23456')
        assert mmr.number('key') == pytest.approx(-1.23456)
