"""
Welch Power Spectral Density estimation for the captured IQ stream.

Public API
----------
    compute_psd(samples) → (f_mhz, pxx_db)
    occupied_bandwidth(f_mhz, pxx_db) → bw_khz, left_khz
"""

import numpy as np
from scipy import signal

from scripts.config import config


def compute_psd(samples):
    f, pxx = signal.welch(
        samples,
        fs=config.sample_rate,
        window='hann',
        nperseg=config.nperseg,
        noverlap=config.noverlap,
        nfft=config.nfft,
        return_onesided=False,
        scaling='density',
    )

    f = np.fft.fftshift(f)
    pxx = np.fft.fftshift(pxx)

    pxx_db = 10 * np.log10(pxx + 1e-18)

    return f / 1e6, pxx_db


def occupied_bandwidth(f_mhz, psd_db, power_frac=0.99):
    """
    Occupied bandwidth via cumulative power method (99% by default).

    Sorts PSD bins by descending power, accumulates until the
    fraction of total power is reached, then takes the min/max
    frequency among those bins.  This matches the standard
    definition of occupied bandwidth in spectrum monitoring.

    Falls back to −20 dB threshold if the power method yields
    an unreasonable result.

    Returns
    -------
        bw_khz  : float   total bandwidth in kHz
        left_khz: float   left edge frequency offset in kHz
    """
    f_khz = np.asarray(f_mhz, dtype=np.float64) * 1000
    pxx_lin = 10 ** (np.asarray(psd_db, dtype=np.float64) / 10)
    total_power = np.sum(pxx_lin)

    if total_power <= 0:
        return 0.0, 0.0

    # Sort bins by linear power (descending)
    order = np.argsort(pxx_lin)[::-1]
    cumsum = np.cumsum(pxx_lin[order])
    thresh = total_power * power_frac
    idx = np.searchsorted(cumsum, thresh)

    if idx >= len(order):
        idx = len(order) - 1

    chosen = order[:idx + 1]
    left_khz = float(np.min(f_khz[chosen]))
    right_khz = float(np.max(f_khz[chosen]))
    bw_khz = right_khz - left_khz

    # Sanity check: fall back to −20 dB method if absurd
    fs_khz = config.sample_rate / 1000
    if bw_khz <= 0 or bw_khz > fs_khz * 0.95:
        peak = np.max(psd_db)
        above = psd_db >= (peak - 20)
        if np.any(above):
            indices = np.where(above)[0]
            left_khz = float(f_khz[indices[0]])
            right_khz = float(f_khz[indices[-1]])
            bw_khz = right_khz - left_khz

    return max(bw_khz, 0.0), left_khz


def clipping_ratio(samples):
    threshold = config.clip_threshold
    real_clip = np.abs(np.real(samples)) > threshold
    imag_clip = np.abs(np.imag(samples)) > threshold
    return np.mean(real_clip | imag_clip)
