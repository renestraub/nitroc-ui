import math

from nitrocui.sig_quality import SignalQuality_LTE


class TestLTE:
    def test_rsrq_1(self):
        q = SignalQuality_LTE._rsrq_to_q(0)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-6.999)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-7)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-10.25)
        assert(math.isclose(q, 0.775))

        q = SignalQuality_LTE._rsrq_to_q(-13.5)
        assert(math.isclose(q, 0.55))

        q = SignalQuality_LTE._rsrq_to_q(-16.75)
        assert(math.isclose(q, 0.325))

        q = SignalQuality_LTE._rsrq_to_q(-20)
        assert(math.isclose(q, 0.10))

        q = SignalQuality_LTE._rsrq_to_q(-20.001)
        assert(math.isclose(q, 0.10))

        q = SignalQuality_LTE._rsrq_to_q(-30)
        assert(math.isclose(q, 0.10))

    def test_rsrp_1(self):
        q = SignalQuality_LTE._rsrp_to_q(0)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrp_to_q(-79.999)
        assert(math.isclose(q, 1.00))

        q = SignalQuality_LTE._rsrp_to_q(-80)
        assert(math.isclose(q, 1.00))

        q = SignalQuality_LTE._rsrp_to_q(-85)
        assert(math.isclose(q, 0.775))

        q = SignalQuality_LTE._rsrp_to_q(-90)
        assert(math.isclose(q, 0.55))

        q = SignalQuality_LTE._rsrp_to_q(-95)
        assert(math.isclose(q, 0.325))

        q = SignalQuality_LTE._rsrp_to_q(-100)
        assert(math.isclose(q, 0.10))

        q = SignalQuality_LTE._rsrp_to_q(-100.001)
        assert(math.isclose(q, 0.10))

        q = SignalQuality_LTE._rsrp_to_q(-140)
        assert(math.isclose(q, 0.10))

    def test_1(self):
        # Excellent
        lte_q = SignalQuality_LTE(-7, -80)
        q = lte_q.quality()
        assert(math.isclose(q, 1.0))

        # Cell edge - Close to disconnection
        lte_q = SignalQuality_LTE(-20, -100)
        q = lte_q.quality()
        print(q)
        assert(math.isclose(q, 0.1))
