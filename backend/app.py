"""
Flask + SocketIO server — serves the SDR PSD dashboard.

Run
---
    python main.py                  (via launcher, starts SDR automatically)
    python main.py --no-sdr         (web UI only)
"""

import time
import threading
import logging

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

from scripts.config import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('sdr-dashboard')

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static',
)

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading',
    logger=False,
    engineio_logger=False,
)

from backend.sdr_manager import manager


# ── Routes ───────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def status():
    return jsonify({
        'running': manager.running,
        'center_freq': config.center_freq,
        'span_khz': config.span_khz,
        'gain': config.gain,
        'nfft': config.nfft,
        'nperseg': config.nperseg,
        'noverlap': config.noverlap,
        'sample_rate': config.sample_rate,
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.get_json()
    if 'center_freq' in data:
        manager.set_frequency(data['center_freq'])
    if 'gain' in data:
        manager.set_gain(data['gain'])
    if 'span_khz' in data:
        manager.set_span(data['span_khz'])
    if 'nfft' in data:
        manager.set_nfft(data['nfft'])
    if 'nperseg' in data:
        manager.set_nperseg(data['nperseg'])
    if 'noverlap' in data:
        manager.set_noverlap(data['noverlap'])
    return jsonify({'ok': True})


@app.route('/api/start', methods=['POST'])
def start_sdr():
    manager.start()
    return jsonify({'running': manager.running})


@app.route('/api/stop', methods=['POST'])
def stop_sdr():
    manager.stop()
    return jsonify({'running': manager.running})


# ── SocketIO — PSD streaming ─────────────────────────────

_psd_thread = None
_psd_stop = threading.Event()
_client_count = 0
_client_lock = threading.Lock()


def _psd_broadcast_loop():
    log.info('PSD broadcast thread started')
    while not _psd_stop.is_set():
        try:
            with _client_lock:
                has_clients = _client_count > 0
            if has_clients and manager.running:
                psd = manager.get_psd()
                if psd is not None:
                    socketio.emit('psd_update', psd)
        except Exception as exc:
            log.error(f'PSD broadcast error: {exc}')
        time.sleep(config.psd_interval)


def _ensure_broadcast_running():
    global _psd_thread
    if _psd_thread is None or not _psd_thread.is_alive():
        _psd_stop.clear()
        _psd_thread = threading.Thread(target=_psd_broadcast_loop, daemon=True)
        _psd_thread.start()


@socketio.on('connect')
def on_connect():
    global _client_count
    with _client_lock:
        _client_count += 1
    _ensure_broadcast_running()
    log.info(f'Client connected (total: {_client_count})')


@socketio.on('disconnect')
def on_disconnect():
    global _client_count
    with _client_lock:
        _client_count = max(0, _client_count - 1)
    log.info(f'Client disconnected (total: {_client_count})')


# ── CLI entry point ─────────────────────────────────────

def run(host='0.0.0.0', port=5000, debug=False):
    print(f'  SDR Dashboard → http://localhost:{port}')
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run(debug=True)
