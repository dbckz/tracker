"""
App Activity Tracker for macOS.
Monitors the currently active application and tracks time spent.
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable

# macOS specific imports - will only work on macOS
try:
    from AppKit import NSWorkspace, NSWorkspaceDidActivateApplicationNotification
    from Foundation import NSRunLoop, NSDate
    from PyObjCTools import AppHelper
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    print("Warning: macOS frameworks not available. App tracking disabled.")


class AppTracker:
    """Tracks active application and time spent in each app."""

    def __init__(self, on_app_change: Optional[Callable] = None, poll_interval: float = 1.0):
        """
        Initialize the app tracker.

        Args:
            on_app_change: Callback function when active app changes.
                          Receives (old_app_info, new_app_info, duration_seconds)
            poll_interval: How often to check for app changes (seconds)
        """
        self.on_app_change = on_app_change
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Current app tracking
        self._current_app = None
        self._current_bundle_id = None
        self._current_window_title = None
        self._app_start_time = None

        # Statistics
        self.total_switches = 0
        self.session_start = None

    def _get_active_app_info(self) -> dict:
        """Get information about the currently active application."""
        if not MACOS_AVAILABLE:
            return {
                'name': 'Unknown',
                'bundle_id': 'unknown',
                'window_title': '',
                'pid': 0
            }

        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.activeApplication() or workspace.frontmostApplication()

        if active_app:
            app_name = active_app.get('NSApplicationName', 'Unknown')
            bundle_id = active_app.get('NSApplicationBundleIdentifier', 'unknown')
            pid = active_app.get('NSApplicationProcessIdentifier', 0)

            # Try to get window title using Accessibility API
            window_title = self._get_window_title(pid)

            return {
                'name': app_name,
                'bundle_id': bundle_id,
                'window_title': window_title,
                'pid': pid
            }

        return {
            'name': 'Unknown',
            'bundle_id': 'unknown',
            'window_title': '',
            'pid': 0
        }

    def _get_window_title(self, pid: int) -> str:
        """Get the title of the frontmost window for a process."""
        if not MACOS_AVAILABLE:
            return ''

        try:
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )

            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )

            for window in window_list:
                if window.get('kCGWindowOwnerPID') == pid:
                    title = window.get('kCGWindowName', '')
                    if title:
                        return title
        except Exception:
            pass

        return ''

    def _tracking_loop(self):
        """Main tracking loop that polls for app changes."""
        while self._running:
            try:
                app_info = self._get_active_app_info()
                current_time = datetime.now()

                # Check if app changed
                if app_info['name'] != self._current_app or \
                   app_info['bundle_id'] != self._current_bundle_id:

                    # Calculate duration for previous app
                    if self._current_app and self._app_start_time:
                        duration = (current_time - self._app_start_time).total_seconds()

                        old_app_info = {
                            'name': self._current_app,
                            'bundle_id': self._current_bundle_id,
                            'window_title': self._current_window_title,
                            'start_time': self._app_start_time,
                            'end_time': current_time,
                            'duration_seconds': duration
                        }

                        # Trigger callback
                        if self.on_app_change:
                            self.on_app_change(old_app_info, app_info, duration)

                        self.total_switches += 1

                    # Update current app
                    self._current_app = app_info['name']
                    self._current_bundle_id = app_info['bundle_id']
                    self._current_window_title = app_info['window_title']
                    self._app_start_time = current_time

                # Update window title if changed (same app, different window)
                elif app_info['window_title'] != self._current_window_title:
                    self._current_window_title = app_info['window_title']

            except Exception as e:
                print(f"Error in tracking loop: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start tracking app activity."""
        if self._running:
            return

        self._running = True
        self.session_start = datetime.now()
        self._app_start_time = self.session_start

        # Get initial app
        app_info = self._get_active_app_info()
        self._current_app = app_info['name']
        self._current_bundle_id = app_info['bundle_id']
        self._current_window_title = app_info['window_title']

        # Start tracking thread
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()

        print(f"App tracking started. Initial app: {self._current_app}")

    def stop(self) -> dict:
        """
        Stop tracking and return final statistics.

        Returns:
            Dictionary with session statistics
        """
        if not self._running:
            return {}

        self._running = False

        # Record final app duration
        if self._current_app and self._app_start_time:
            end_time = datetime.now()
            duration = (end_time - self._app_start_time).total_seconds()

            final_app_info = {
                'name': self._current_app,
                'bundle_id': self._current_bundle_id,
                'window_title': self._current_window_title,
                'start_time': self._app_start_time,
                'end_time': end_time,
                'duration_seconds': duration
            }

            if self.on_app_change:
                self.on_app_change(final_app_info, None, duration)

        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=2.0)

        session_duration = (datetime.now() - self.session_start).total_seconds() if self.session_start else 0

        return {
            'session_duration': session_duration,
            'total_switches': self.total_switches,
            'final_app': self._current_app
        }

    def get_current_app(self) -> dict:
        """Get information about the currently tracked app."""
        if not self._current_app:
            return self._get_active_app_info()

        current_time = datetime.now()
        duration = (current_time - self._app_start_time).total_seconds() if self._app_start_time else 0

        return {
            'name': self._current_app,
            'bundle_id': self._current_bundle_id,
            'window_title': self._current_window_title,
            'start_time': self._app_start_time,
            'current_duration': duration
        }

    @property
    def is_running(self) -> bool:
        """Check if tracker is currently running."""
        return self._running


# Browser detection helpers
BROWSER_BUNDLE_IDS = {
    'com.apple.Safari': 'Safari',
    'com.google.Chrome': 'Chrome',
    'org.mozilla.firefox': 'Firefox',
    'com.microsoft.edgemac': 'Edge',
    'com.brave.Browser': 'Brave',
    'com.operasoftware.Opera': 'Opera',
    'com.vivaldi.Vivaldi': 'Vivaldi',
    'company.thebrowser.Browser': 'Arc',
}


def is_browser(bundle_id: str) -> bool:
    """Check if the given bundle ID is a known browser."""
    return bundle_id in BROWSER_BUNDLE_IDS


def get_browser_name(bundle_id: str) -> Optional[str]:
    """Get the browser name from bundle ID."""
    return BROWSER_BUNDLE_IDS.get(bundle_id)
