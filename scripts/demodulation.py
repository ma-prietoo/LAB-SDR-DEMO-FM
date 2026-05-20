"""
FM demodulation DSP chain — ported from lab.py with identical behaviour.

Processing pipeline
-------------------
    IQ samples → RF lowpass → FM polar discriminator
    → decimation (240k→48k) → audio lowpass
    → de-emphasis → DC removal → normalisation
"""

import numpy as np
from scipy import signal

from scripts.config import config


# ── Module-level filter coefficients (built once, reused) ──
_sos_rf = None
_sos_audio = None
_sos_decim = None
_de_b = None
_de_a = None

# ── Filter states (persist across calls) ──
_rf_zi = None
_decim_zi = None
_audio_zi = None
_deemph_zi = None


def _build_filters():
    global _sos_rf, _sos_audio, _sos_decim, _de_b, _de_a

    _sos_rf = signal.butter(
        config.rf_filter_order,
        config.rf_bpf_cutoff,
        btype='low',
        fs=config.sample_rate,
        output='sos',
    )

    _sos_audio = signal.butter(
        config.audio_lpf_order,
        config.audio_lpf_cutoff,
        btype='low',
        fs=config.audio_rate,
        output='sos',
    )

    _sos_decim = signal.butter(
        config.decim_filter_order,
        config.decim_filter_cutoff,
        btype='low',
        output='sos',
    )

    alpha = np.exp(-1.0 / (config.deemph_tau * config.audio_rate))
    _de_b = [1.0 - alpha]
    _de_a = [1.0, -alpha]


def fm_demodulate(samples):
    phase = np.angle(samples[1:] * np.conj(samples[:-1]))
    return phase * config.sample_rate / (2 * np.pi)


def process_audio(samples):
    global _rf_zi, _decim_zi, _audio_zi, _deemph_zi

    if _sos_rf is None:
        _build_filters()

    # ── RF lowpass ──────────────────────────────────────
    if _rf_zi is None:
        _rf_zi = signal.sosfilt_zi(_sos_rf) * samples[0]
    filtered, _rf_zi = signal.sosfilt(_sos_rf, samples, zi=_rf_zi)

    # ── FM demod ────────────────────────────────────────
    audio = fm_demodulate(filtered)

    # ── Decimation 240k → 48k ──────────────────────────
    if _decim_zi is None:
        _decim_zi = signal.sosfilt_zi(_sos_decim) * audio[0]
    decimated, _decim_zi = signal.sosfilt(_sos_decim, audio, zi=_decim_zi)
    decimated = decimated[::config.decim_factor]

    # ── Audio lowpass ───────────────────────────────────
    if _audio_zi is None:
        _audio_zi = signal.sosfilt_zi(_sos_audio) * decimated[0]
    audio_filt, _audio_zi = signal.sosfilt(_sos_audio, decimated, zi=_audio_zi)

    # ── De-emphasis ─────────────────────────────────────
    if _deemph_zi is None:
        _deemph_zi = signal.lfilter_zi(_de_b, _de_a) * audio_filt[0]
    deemph, _deemph_zi = signal.lfilter(_de_b, _de_a, audio_filt, zi=_deemph_zi)

    # ── DC removal + normalisation ─────────────────────
    deemph = deemph - np.mean(deemph)
    peak = np.max(np.abs(deemph)) + 1e-12
    deemph = deemph / peak * 0.7

    return deemph.astype(np.float32)


def reset_filter_states():
    global _rf_zi, _decim_zi, _audio_zi, _deemph_zi
    global _sos_rf, _sos_audio, _sos_decim, _de_b, _de_a
    _rf_zi = _decim_zi = _audio_zi = _deemph_zi = None
    _sos_rf = _sos_audio = _sos_decim = None
    _de_b = _de_a = None
