"""
Audio output via sounddevice — runs in a background thread.

Public API
----------
    start_audio(iq_queue, stop_event)
        Launches the audio processing + playback thread.
"""

import threading
import queue

import numpy as np
import sounddevice as sd

from scripts.config import config
from scripts.demodulation import process_audio


def _audio_loop(iq_queue, stop_event):

    stream = sd.OutputStream(
        samplerate=config.audio_rate,
        channels=1,
        dtype='float32',
        blocksize=4096,
        latency='high',
    )
    stream.start()

    try:
        while not stop_event.is_set():
            try:
                samples = iq_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            audio = process_audio(samples)
            stream.write(audio)
    finally:
        stream.stop()
        stream.close()


def start_audio(iq_queue, stop_event):

    th = threading.Thread(
        target=_audio_loop,
        args=(iq_queue, stop_event),
        daemon=True,
    )
    th.start()
    return th
