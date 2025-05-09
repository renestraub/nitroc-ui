class CellularSignalQuality:
    # Define ranges for each parameter as class-level constants
    RSRP_MIN, RSRP_MAX = -120.0, -80.0  # RSRP range in dBm
    RSRQ_MIN, RSRQ_MAX = -30.0, 0.0     # RSRQ range in dB
    SNR_MIN, SNR_MAX = -10.0, 30.0      # S/N range in dB

    @staticmethod
    def compute_signal_quality(rsrp: float, rsrq: float, snr: float) -> int:
        """
        Compute a 0–100 signal quality value based on RSRP, RSRQ, and S/N.

        Args:
        rsrp (float): Reference Signal Received Power (in dBm).
        rsrq (float): Reference Signal Received Quality (in dB).
        snr (float): Signal-to-Noise Ratio (in dB).

        Returns:
        int: Signal quality as a value between 0 and 100.
        """
        # Normalize each parameter to a 0–1 scale
        rsrp_score = max(0, min(1, (rsrp - CellularSignalQuality.RSRP_MIN) / (CellularSignalQuality.RSRP_MAX - CellularSignalQuality.RSRP_MIN)))
        rsrq_score = max(0, min(1, (rsrq - CellularSignalQuality.RSRQ_MIN) / (CellularSignalQuality.RSRQ_MAX - CellularSignalQuality.RSRQ_MIN)))
        snr_score = max(0, min(1, (snr - CellularSignalQuality.SNR_MIN) / (CellularSignalQuality.SNR_MAX - CellularSignalQuality.SNR_MIN)))

        # Assign higher weights to RSRQ and SNR
        RSRP_WEIGHT = 0.25
        RSRQ_WEIGHT = 0.4
        SNR_WEIGHT = 0.35

        # Compute the weighted average
        quality_score = (
            rsrp_score * RSRP_WEIGHT +
            rsrq_score * RSRQ_WEIGHT +
            snr_score * SNR_WEIGHT
        )

        # Scale to 0–100 and return as an integer
        return int(quality_score * 100)

    @staticmethod
    def limit_signal(value: float) -> float:
        """
        Clamp the signal value (RSRP) to the valid range.

        Args:
        value (float): The signal value to validate.

        Returns:
        float: The clamped value within the range [RSRP_MIN, RSRP_MAX].
        """
        return max(CellularSignalQuality.RSRP_MIN, min(CellularSignalQuality.RSRP_MAX, value))

    @staticmethod
    def limit_rsrq(value: float) -> float:
        """
        Clamp the RSRQ value to the valid range.

        Args:
        value (float): The RSRQ value to validate.

        Returns:
        float: The clamped value within the range [RSRQ_MIN, RSRQ_MAX].
        """
        return max(CellularSignalQuality.RSRQ_MIN, min(CellularSignalQuality.RSRQ_MAX, value))

    @staticmethod
    def limit_snr(value: float) -> float:
        """
        Clamp the SNR value to the valid range.

        Args:
        value (float): The SNR value to validate.

        Returns:
        float: The clamped value within the range [SNR_MIN, SNR_MAX].
        """
        return max(CellularSignalQuality.SNR_MIN, min(CellularSignalQuality.SNR_MAX, value))
