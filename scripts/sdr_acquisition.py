"""
RTL-SDR acquisition — captures IQ samples in a background thread.
The SDR handle is exposed for runtime frequency/gain changes.
On stop, the capture thread closes the device in its finally block.
"""

import threading
import logging

import numpy as np
from rtlsdr import RtlSdr

from scripts.config import config

log = logging.getLogger('sdr-acquisition')


def _capture_loop(sdr, iq_queue, viz_buffer, viz_lock, stop_event):
    try:
        log.info(
            'SDR ready: freq=%.1f MHz, fs=%.0f kHz, gain=%.1f dB',
            config.center_freq, config.sample_rate / 1e3, config.gain,
        )
        while not stop_event.is_set():
            block = config.capture_block
            samples = sdr.read_samples(block)
            samples = samples - np.mean(samples)

            try:
                iq_queue.put_nowait(samples)
            except Exception:
                pass

            with viz_lock:
                viz_buffer.extend(samples)

    except Exception as exc:
        if not stop_event.is_set():
            log.error('Capture error: %s', exc)
    finally:
        try:
            sdr.close()
        except Exception:
            pass
        log.info('Capture thread closed SDR and exited')


def start_capture(iq_queue, viz_buffer, viz_lock, stop_event):
    sdr = RtlSdr()
    sdr.sample_rate = config.sample_rate
    sdr.center_freq = config.center_freq * 1e6
    sdr.gain = config.gain

    th = threading.Thread(
        target=_capture_loop,
        args=(sdr, iq_queue, viz_buffer, viz_lock, stop_event),
        daemon=True,
    )
    th.start()
    return sdr, th


def update_sdr_frequency(sdr, freq_mhz):
    sdr.center_freq = freq_mhz * 1e6
    config.center_freq = freq_mhz
    log.info('Frequency → %.3f MHz', freq_mhz)


def update_sdr_gain(sdr, gain_db):
    sdr.gain = gain_db
    config.gain = gain_db
    log.info('Gain → %.1f dB', gain_db)
