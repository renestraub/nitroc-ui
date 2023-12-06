
class SignalQuality_LTE:
    q_max = 1.0
    q_min = 0.1

    def __init__(self, rsrq, rsrp):
        self._rsrq = rsrq
        self._rsrp = rsrp

        q_rsrq = SignalQuality_LTE._rsrq_to_q(self._rsrq)
        # q_rsrp = SignalQuality_LTE._rsrp_to_q(self._rsrp)

        # Use RSRQ only as quality indicator
        self._quality = q_rsrq

        # Weigh RSRQ 2x and RSRP 1x
        # self._quality = (2.0 * q_rsrq + q_rsrp) / 3.0

    def quality(self):
        return self._quality

    @classmethod
    def _rsrq_to_q(cls, rsrq):
        """
        Maps LTE RSRQ to a 0..1 quality indicator
        - >=  -7: 1.0 Excellent
        -  < -20: 0.1 Cell Edge
        - Values in between are linear interpolated
        """
        rsrq_high = -7
        rsrq_low = -20
        if rsrq > rsrq_high:
            q = cls.q_max
        elif rsrq < rsrq_low:
            q = cls.q_min
        else:
            q = 1.0+((rsrq-rsrq_high)/(rsrq_high-rsrq_low)*(cls.q_max-cls.q_min))

        return q

    @classmethod
    def _rsrp_to_q(cls, rsrp):
        """
        Maps LTE RSRP to a 0..1 quality indicator

        -  >= -80: 1.0 Excellent
        -  < -100: 0.1 Cell Edge
        - Values in between are linear interpolated
        """
        rsrp_high = -80
        rsrp_low = -100
        if rsrp > rsrp_high:
            q = cls.q_max
        elif rsrp < rsrp_low:
            q = cls.q_min
        else:
            q = 1.0+((rsrp-rsrp_high)/(rsrp_high-rsrp_low)*(cls.q_max-cls.q_min))

        return q
