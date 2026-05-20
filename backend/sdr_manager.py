"""
SDR Manager — orchestrates the full signal pipeline behind the Flask server.
"""

import time
import threading
import queue
import logging
from collections import deque

import numpy as np

from scripts.config import config
from scripts.sdr_acquisition import start_capture, update_sdr_frequency, update_sdr_gain
from scripts.audio_player import start_audio
from scripts.psd import compute_psd, clipping_ratio, occupied_bandwidth

log = logging.getLogger('sdr-manager')


class SDRManager:

    def __init__(self):
        self.sdr = None
        self.capture_th = None
        self.audio_th = None

        self.iq_queue = queue.Queue(maxsize=256)
        self.viz_buffer = deque(maxlen=config.n_samples)
        self.viz_lock = threading.Lock()

        self._capture_stop = threading.Event()
        self._audio_stop = threading.Event()
        self._running = False

    # ── Lifecycle ────────────────────────────────────────

    def start(self):
        if self._running:
            return

        self._capture_stop.clear()
        self._audio_stop.clear()

        log.info('Starting SDR pipeline ...')
        self.sdr, self.capture_th = start_capture(
            self.iq_queue, self.viz_buffer, self.viz_lock, self._capture_stop,
        )
        time.sleep(0.5)
        self.audio_th = start_audio(self.iq_queue, self._audio_stop)
        self._running = True
        log.info('SDR pipeline running')

    def stop(self):
        if not self._running:
            return
        log.info('Stopping SDR pipeline ...')
        self._capture_stop.set()
        self._audio_stop.set()

        if self.capture_th and self.capture_th.is_alive():
            self.capture_th.join(timeout=4.0)

        self._running = False
        self.sdr = None
        log.info('SDR pipeline stopped')

    @property
    def running(self):
        return self._running

    # ── PSD snapshot ─────────────────────────────────────

    def get_psd(self):
        with self.viz_lock:
            n = len(self.viz_buffer)
            if n < config.nperseg:
                return None
            snap = np.array(list(self.viz_buffer), dtype=np.complex64)
            self.viz_buffer.clear()

        f_mhz, pxx_db = compute_psd(snap)
        clip = clipping_ratio(snap)
        bw_khz, bw_left_khz = occupied_bandwidth(f_mhz, pxx_db)

        return {
            'freq_mhz': f_mhz.tolist(),
            'psd_db': [float(v) for v in pxx_db],
            'center_freq': config.center_freq,
            'span_khz': config.span_khz,
            'gain': config.gain,
            'clipping': float(clip),
            'bw_khz': bw_khz,
            'bw_left_khz': bw_left_khz,
        }

    # ── Configuration helpers ─────────────────────────────

    def set_frequency(self, freq_mhz):
        config.center_freq = float(freq_mhz)
        if self.sdr is not None:
            update_sdr_frequency(self.sdr, freq_mhz)

    def set_gain(self, gain_db):
        config.gain = float(gain_db)
        if self.sdr is not None:
            update_sdr_gain(self.sdr, gain_db)

    def set_span(self, span_khz):
        config.span_khz = float(span_khz)

    def set_nfft(self, nfft):
        config.nfft = int(nfft)

    def set_nperseg(self, nperseg):
        config.nperseg = int(nperseg)

    def set_noverlap(self, noverlap):
        config.noverlap = int(noverlap)


manager = SDRManager()
