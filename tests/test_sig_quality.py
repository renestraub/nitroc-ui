import math
from nitrocui.cellular_signal_quality import CellularSignalQuality


class TestLimits:
    def test_limit_signal(self):
        # Test values within the range
        assert CellularSignalQuality.limit_signal(-120) == -120
        assert CellularSignalQuality.limit_signal(-100) == -100
        assert CellularSignalQuality.limit_signal(-80) == -80

        # Test values outside the range
        assert CellularSignalQuality.limit_signal(-130) == -120  # Clamped to lower bound
        assert CellularSignalQuality.limit_signal(-70) == -80    # Clamped to upper bound

    def test_limit_rsrq(self):
        # Test values within the range
        assert CellularSignalQuality.limit_rsrq(-30) == -30
        assert CellularSignalQuality.limit_rsrq(-15) == -15
        assert CellularSignalQuality.limit_rsrq(0) == 0

        # Test values outside the range
        assert CellularSignalQuality.limit_rsrq(-35) == -30  # Clamped to lower bound
        assert CellularSignalQuality.limit_rsrq(5) == 0      # Clamped to upper bound

    def test_limit_snr(self):
        # Test values within the range
        assert CellularSignalQuality.limit_snr(-10) == -10
        assert CellularSignalQuality.limit_snr(0) == 0
        assert CellularSignalQuality.limit_snr(30) == 30

        # Test values outside the range
        assert CellularSignalQuality.limit_snr(-15) == -10  # Clamped to lower bound
        assert CellularSignalQuality.limit_snr(40) == 30    # Clamped to upper bound


class TestComputeSignalQuality:
    def test_perfect_signal(self):
        # Perfect signal values
        rsrp = -80  # Maximum RSRP
        rsrq = 0    # Maximum RSRQ
        snr = 30    # Maximum SNR
        quality = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)
        assert quality == 100, f"Expected 100, got {quality}"

    def test_poor_signal(self):
        # Poor signal values
        rsrp = -120  # Minimum RSRP
        rsrq = -30   # Minimum RSRQ
        snr = -10    # Minimum SNR
        quality = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)
        assert quality == 0, f"Expected 0, got {quality}"

    def test_average_signal(self):
        # Average signal values
        rsrp = -100
        rsrq = -15
        snr = 15
        quality = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)
        assert 50 <= quality <= 60, f"Expected quality in range 50-60, got {quality}"

    def test_partial_signal(self):
        # Partial signal with one parameter at max, others at min
        rsrp = -80
        rsrq = -30
        snr = -10
        quality = CellularSignalQuality.compute_signal_quality(rsrp, rsrq, snr)
        assert 20 <= quality <= 30, f"Expected quality in range 20-30, got {quality}"