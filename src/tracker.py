"""
Main Activity Tracker Controller.
Coordinates all tracking components and manages the application lifecycle.
"""

import threading
import time
import signal
import sys
from datetime import datetime, date
from typing import Optional

from .database import Database
from .trackers.app_tracker import AppTracker
from .trackers.browser_tracker import BrowserTracker
from .trackers.typing_tracker import TypingTracker, TypingTrackerSimulated, MACOS_AVAILABLE
from .analytics.analyzer import ActivityAnalyzer


class ActivityTrackerController:
    """Main controller that manages all tracking components."""

    def __init__(self, db_path: str = None):
        """Initialize the tracker controller."""
        self.db = Database(db_path)
        self.analyzer = ActivityAnalyzer(self.db)

        # Initialize trackers
        self.app_tracker = AppTracker(
            on_app_change=self._on_app_change,
            poll_interval=1.0
        )

        self.browser_tracker = BrowserTracker(
            on_site_change=self._on_site_change,
            poll_interval=2.0
        )

        # Use real or simulated typing tracker
        if MACOS_AVAILABLE:
            self.typing_tracker = TypingTracker(
                on_stats_update=self._on_typing_update,
                wpm_window_seconds=60,
                stats_callback_interval=30.0
            )
        else:
            self.typing_tracker = TypingTrackerSimulated(
                on_stats_update=self._on_typing_update,
                wpm_window_seconds=60,
                stats_callback_interval=30.0
            )

        # State tracking
        self._running = False
        self._paused = False
        self._current_app_id: Optional[int] = None
        self._current_site_id: Optional[int] = None

        # Session stats
        self.session_start: Optional[datetime] = None
        self._session_words = 0
        self._session_keystrokes = 0

        # Lock for thread safety
        self._lock = threading.Lock()

    def _on_app_change(self, old_app_info: dict, new_app_info: dict, duration: float):
        """Handle app change events."""
        if self._paused:
            return

        with self._lock:
            # Record completed app session
            if old_app_info and duration > 0:
                try:
                    self.db.record_app_activity(
                        app_name=old_app_info['name'],
                        app_bundle_id=old_app_info.get('bundle_id', ''),
                        window_title=old_app_info.get('window_title', ''),
                        start_time=old_app_info['start_time'],
                        end_time=old_app_info['end_time'],
                        duration_seconds=duration
                    )
                except Exception as e:
                    print(f"Error recording app activity: {e}")

    def _on_site_change(self, old_site_info: dict, new_site_info: dict, duration: float):
        """Handle website change events."""
        if self._paused:
            return

        with self._lock:
            # Record completed site session
            if old_site_info and duration > 0:
                try:
                    self.db.record_website_activity(
                        url=old_site_info.get('url', ''),
                        domain=old_site_info.get('domain', ''),
                        page_title=old_site_info.get('title', ''),
                        browser=old_site_info.get('browser', ''),
                        start_time=old_site_info['start_time'],
                        end_time=old_site_info['end_time'],
                        duration_seconds=duration
                    )
                except Exception as e:
                    print(f"Error recording website activity: {e}")

    def _on_typing_update(self, stats: dict):
        """Handle typing statistics updates."""
        if self._paused:
            return

        with self._lock:
            keystrokes = stats.get('window_keystrokes', 0)
            words = stats.get('window_words', 0)
            current_app = stats.get('current_app', '')

            # Update session totals
            self._session_keystrokes += keystrokes
            self._session_words += words

            # Record to database
            try:
                if keystrokes > 0 or words > 0:
                    self.db.increment_typing_stats(
                        keystrokes=keystrokes,
                        words=words,
                        app_name=current_app
                    )
            except Exception as e:
                print(f"Error recording typing stats: {e}")

    def start(self):
        """Start all tracking components."""
        if self._running:
            print("Tracker is already running.")
            return

        self._running = True
        self.session_start = datetime.now()

        print("\n" + "=" * 50)
        print("Mac Activity Tracker Starting...")
        print("=" * 50)

        # Start trackers
        self.app_tracker.start()
        self.browser_tracker.start()
        self.typing_tracker.start()

        print("\nTracking active:")
        print("  - Application usage")
        print("  - Website activity")
        print("  - Typing statistics")
        print("\nData stored at:", self.db.db_path)
        print("Dashboard available at: http://127.0.0.1:5050")
        print("\nPress Ctrl+C to stop\n")

    def stop(self):
        """Stop all tracking and save final data."""
        if not self._running:
            return

        print("\nStopping tracker...")

        self._running = False

        # Stop all trackers
        app_stats = self.app_tracker.stop()
        site_stats = self.browser_tracker.stop()
        typing_stats = self.typing_tracker.stop()

        # Calculate session duration
        session_duration = 0
        if self.session_start:
            session_duration = (datetime.now() - self.session_start).total_seconds()

        print("\n" + "=" * 50)
        print("Session Summary")
        print("=" * 50)
        print(f"Duration: {session_duration / 3600:.1f} hours")
        print(f"App switches: {app_stats.get('total_switches', 0)}")
        print(f"Site changes: {site_stats.get('total_site_changes', 0)}")
        print(f"Total keystrokes: {typing_stats.get('total_keystrokes', 0):,}")
        print(f"Total words: {typing_stats.get('total_words', 0):,}")
        print("=" * 50 + "\n")

    def pause(self):
        """Pause tracking without stopping."""
        self._paused = True
        print("Tracking paused.")

    def resume(self):
        """Resume tracking after pause."""
        self._paused = False
        print("Tracking resumed.")

    @property
    def is_paused(self) -> bool:
        """Check if tracking is paused."""
        return self._paused

    @property
    def is_running(self) -> bool:
        """Check if tracker is running."""
        return self._running

    def get_quick_stats(self) -> dict:
        """Get quick stats for menu bar display."""
        today = date.today()

        app_summary = self.analyzer.get_app_summary_for_date(today)
        typing_summary = self.analyzer.get_typing_summary_for_date(today)

        return {
            'active_hours': app_summary.get('total_hours', 0),
            'words_today': typing_summary.get('total_words', 0)
        }

    def get_today_summary(self) -> dict:
        """Get comprehensive summary for today."""
        today = date.today()

        app_summary = self.analyzer.get_app_summary_for_date(today)
        typing_summary = self.analyzer.get_typing_summary_for_date(today)

        return {
            'total_hours': app_summary.get('total_hours', 0),
            'app_count': app_summary.get('app_count', 0),
            'total_words': typing_summary.get('total_words', 0),
            'avg_wpm': typing_summary.get('average_wpm', 0)
        }

    def get_session_stats(self) -> dict:
        """Get current session statistics."""
        current_app = self.app_tracker.get_current_app()
        session_minutes = 0

        if self.session_start:
            session_minutes = (datetime.now() - self.session_start).total_seconds() / 60

        return {
            'current_app': current_app.get('name', 'Unknown'),
            'session_minutes': session_minutes,
            'session_words': self._session_words,
            'session_keystrokes': self._session_keystrokes
        }


def create_tracker(db_path: str = None) -> ActivityTrackerController:
    """Factory function to create a tracker instance."""
    return ActivityTrackerController(db_path)
