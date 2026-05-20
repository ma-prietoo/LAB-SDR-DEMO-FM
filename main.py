#!/usr/bin/env python3
"""
SDR FM Receiver — Real-time Welch PSD Dashboard (Flask + SocketIO).

Usage
-----
    python main.py                 # starts everything
    python main.py --no-sdr        # only the web server (demo mode)
    python main.py --port 8080     # custom port
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app, socketio, run as flask_run
from backend.sdr_manager import manager


def main():
    parser = argparse.ArgumentParser(description='SDR PSD Dashboard')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--no-sdr', action='store_true',
                        help='Skip SDR initialisation (web UI only)')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    if not args.no_sdr:
        print('  Starting RTL-SDR capture & audio pipeline ...')
        manager.start()
        print('  SDR pipeline running.')
    else:
        print('  --no-sdr flag set — skipping RTL-SDR initialisation.')

    try:
        flask_run(host=args.host, port=args.port, debug=args.debug)
    finally:
        manager.stop()
        print('  SDR pipeline stopped.')


if __name__ == '__main__':
    main()
