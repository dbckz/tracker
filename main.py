#!/usr/bin/env python3
"""
Mac Activity Tracker - Main Entry Point

A local activity tracking application that monitors:
- Application usage and time spent
- Website visits and browsing patterns
- Typing statistics (words, WPM)

All data is stored locally in SQLite.

Usage:
    python main.py              # Start tracker with web dashboard
    python main.py --dashboard  # Start only the dashboard (view existing data)
    python main.py --menu-bar   # Start with menu bar integration
"""

import argparse
import os
import signal
import sys
import threading
import webbrowser
from time import sleep

from src.tracker import ActivityTrackerController
from src.database import Database
from src.web.app import run_dashboard


def signal_handler(signum, frame, tracker=None):
    """Handle shutdown signals gracefully."""
    print("\n\nReceived shutdown signal...")
    if tracker:
        tracker.stop()
    sys.exit(0)


def get_dashboard_url(port: int) -> str:
    """Get the best URL for the dashboard (custom hostname if available)."""
    import socket
    # Check if tracker.local resolves (custom hostname set up)
    try:
        socket.gethostbyname('tracker.local')
        return f'http://tracker.local:{port}'
    except socket.gaierror:
        return f'http://localhost:{port}'


def run_with_dashboard(tracker: ActivityTrackerController, port: int = 5050,
                      open_browser: bool = True, host: str = '0.0.0.0'):
    """Run tracker with web dashboard."""
    # Start the tracker
    tracker.start()

    # Start dashboard in a thread (bind to 0.0.0.0 to accept custom hostnames)
    dashboard_thread = threading.Thread(
        target=run_dashboard,
        kwargs={'host': host, 'port': port, 'debug': False, 'db': tracker.db},
        daemon=True
    )
    dashboard_thread.start()

    # Open browser after a short delay
    if open_browser:
        sleep(1.5)
        webbrowser.open(get_dashboard_url(port))

    # Keep running until interrupted
    try:
        while tracker.is_running:
            sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()


def run_with_menu_bar(tracker: ActivityTrackerController, port: int = 5050):
    """Run tracker with menu bar integration."""
    from src.menu_bar import run_menu_bar, RUMPS_AVAILABLE

    if not RUMPS_AVAILABLE:
        print("Menu bar integration requires the 'rumps' package.")
        print("Install it with: pip install rumps")
        print("\nFalling back to dashboard mode...")
        run_with_dashboard(tracker, port)
        return

    # Start the tracker
    tracker.start()

    # Start dashboard in background (bind to 0.0.0.0 for custom hostnames)
    dashboard_thread = threading.Thread(
        target=run_dashboard,
        kwargs={'host': '0.0.0.0', 'port': port, 'debug': False, 'db': tracker.db},
        daemon=True
    )
    dashboard_thread.start()

    # Run menu bar (this blocks)
    try:
        run_menu_bar(tracker)
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()


def run_dashboard_only(port: int = 5050, open_browser: bool = True):
    """Run only the dashboard to view existing data."""
    db = Database()
    print("\n📊 Starting Activity Dashboard (view mode)")
    print(f"   Database: {db.db_path}")
    print(f"   URL: {get_dashboard_url(port)}")

    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(get_dashboard_url(port))).start()

    run_dashboard(host='0.0.0.0', port=port, debug=False, db=db)


def main():
    parser = argparse.ArgumentParser(
        description='Mac Activity Tracker - Monitor your computer usage locally',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                    Start tracker with web dashboard
    python main.py --dashboard        View existing data (no tracking)
    python main.py --menu-bar         Start with system menu bar icon
    python main.py --port 8080        Use custom port for dashboard

Notes:
    - All data is stored locally in ~/.mac_activity_tracker/
    - Requires Accessibility permissions for typing tracking
    - Dashboard available at http://127.0.0.1:5050 by default
        """
    )

    parser.add_argument(
        '--dashboard', '-d',
        action='store_true',
        help='Start only the dashboard (view mode, no tracking)'
    )

    parser.add_argument(
        '--menu-bar', '-m',
        action='store_true',
        help='Start with system menu bar integration'
    )

    parser.add_argument(
        '--port', '-p',
        type=int,
        default=int(os.getenv('PORT', 5050)),
        help='Port for the web dashboard (default: 5050 or PORT env var)'
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open the browser'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='Custom database path'
    )

    args = parser.parse_args()

    # Dashboard only mode
    if args.dashboard:
        run_dashboard_only(port=args.port, open_browser=not args.no_browser)
        return

    # Create tracker
    tracker = ActivityTrackerController(db_path=args.db_path)

    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, tracker))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, tracker))

    # Run with menu bar or dashboard
    if args.menu_bar:
        run_with_menu_bar(tracker, port=args.port)
    else:
        run_with_dashboard(tracker, port=args.port, open_browser=not args.no_browser)


if __name__ == '__main__':
    main()
