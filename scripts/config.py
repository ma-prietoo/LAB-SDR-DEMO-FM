"""
Global configuration for the SDR FM receiver pipeline.
All tunable parameters live here — changed at runtime via the web UI.
"""

from dataclasses import dataclass, field


@dataclass
class SDRConfig:
    # ── RTL-SDR ──────────────────────────────────────────
    center_freq: float = 105.7            # MHz
    sample_rate: int = 240000             # 240 kS/s
    capture_block: int = 16384            # samples per read
    gain: float = 20.0                    # dB
    gain_min: float = 0.0
    gain_max: float = 49.6

    # ── Audio ───────────────────────────────────────────
    audio_rate: int = 48000               # 48 kHz
    fm_deviation: float = 75000
    deemph_tau: float = 75e-6

    # ── RF filter ───────────────────────────────────────
    rf_bpf_cutoff: float = 100e3          # Hz
    rf_filter_order: int = 5

    # ── Audio lowpass ───────────────────────────────────
    audio_lpf_cutoff: float = 16000
    audio_lpf_order: int = 6

    # ── Decimation ──────────────────────────────────────
    decim_factor: int = 5                 # 240k → 48k
    decim_filter_cutoff: float = 0.35     # normalised
    decim_filter_order: int = 6

    # ── PSD (Welch) ─────────────────────────────────────
    nfft: int = 2048
    nperseg: int = 2048
    noverlap: int = 1024
    span_khz: float = 0.0                 # kHz shown on PSD plot (0 = auto-scale)
    n_samples: int = 65536                # max buffer size
    psd_interval: float = 1.0             # seconds between PSD updates

    # ── Clipping guard ──────────────────────────────────
    clip_threshold: float = 0.95


# Mutable global instance — threads read from it; UI writes to it
config = SDRConfig()
