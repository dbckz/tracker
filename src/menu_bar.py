"""
Menu Bar Application for Mac Activity Tracker.
Provides a system tray icon with quick access to stats and controls.
"""

import socket
import webbrowser
import threading
from datetime import datetime


def get_dashboard_url(port: int = 5050) -> str:
    """Get the best URL for the dashboard."""
    try:
        socket.gethostbyname('tracker.local')
        return f'http://tracker.local:{port}'
    except socket.gaierror:
        return f'http://localhost:{port}'

try:
    import rumps
    RUMPS_AVAILABLE = True
except ImportError:
    RUMPS_AVAILABLE = False
    print("Warning: rumps not available. Menu bar integration disabled.")


class ActivityTrackerMenuBar(rumps.App if RUMPS_AVAILABLE else object):
    """Menu bar application for the activity tracker."""

    def __init__(self, tracker_controller=None):
        if not RUMPS_AVAILABLE:
            return

        super().__init__(
            name="Activity Tracker",
            icon=None,  # Will use text as icon
            title="AT",
            quit_button=None  # Custom quit to save data
        )

        self.tracker = tracker_controller
        self._update_interval = 30  # seconds

        # Build menu
        self.menu = [
            rumps.MenuItem('Status: Running', callback=None),
            None,  # Separator
            rumps.MenuItem('Today\'s Stats', callback=self.show_today_stats),
            rumps.MenuItem('Current Session', callback=self.show_session_stats),
            None,
            rumps.MenuItem('Open Dashboard', callback=self.open_dashboard),
            None,
            rumps.MenuItem('Pause Tracking', callback=self.toggle_tracking),
            rumps.MenuItem('Quit', callback=self.quit_app)
        ]

        # Start timer for updating stats
        self._timer = rumps.Timer(self.update_title, self._update_interval)
        self._timer.start()

    def update_title(self, sender=None):
        """Update the menu bar title with current stats."""
        if self.tracker:
            try:
                stats = self.tracker.get_quick_stats()
                hours = stats.get('active_hours', 0)
                words = stats.get('words_today', 0)

                # Show hours and word count in title
                if hours > 0 or words > 0:
                    self.title = f"{hours:.1f}h | {words}w"
                else:
                    self.title = "AT"
            except Exception:
                self.title = "AT"

    @rumps.clicked('Today\'s Stats')
    def show_today_stats(self, sender=None):
        """Show today's statistics in a notification."""
        if not self.tracker:
            rumps.notification(
                title="Activity Tracker",
                subtitle="No Stats Available",
                message="Tracker not initialized"
            )
            return

        try:
            stats = self.tracker.get_today_summary()
            message = (
                f"Active: {stats.get('total_hours', 0):.1f} hours\n"
                f"Apps used: {stats.get('app_count', 0)}\n"
                f"Words typed: {stats.get('total_words', 0):,}\n"
                f"Avg WPM: {stats.get('avg_wpm', 0):.0f}"
            )
            rumps.notification(
                title="Today's Activity",
                subtitle=datetime.now().strftime("%A, %B %d"),
                message=message
            )
        except Exception as e:
            rumps.notification(
                title="Activity Tracker",
                subtitle="Error",
                message=str(e)
            )

    @rumps.clicked('Current Session')
    def show_session_stats(self, sender=None):
        """Show current session statistics."""
        if not self.tracker:
            return

        try:
            session = self.tracker.get_session_stats()
            current_app = session.get('current_app', 'Unknown')
            session_minutes = session.get('session_minutes', 0)
            words = session.get('session_words', 0)

            message = (
                f"Current app: {current_app}\n"
                f"Session: {session_minutes:.0f} minutes\n"
                f"Words this session: {words:,}"
            )
            rumps.notification(
                title="Current Session",
                subtitle="Activity Tracker",
                message=message
            )
        except Exception as e:
            print(f"Error showing session stats: {e}")

    @rumps.clicked('Open Dashboard')
    def open_dashboard(self, sender=None):
        """Open the web dashboard in browser."""
        webbrowser.open(get_dashboard_url())

    @rumps.clicked('Pause Tracking')
    def toggle_tracking(self, sender):
        """Toggle tracking on/off."""
        if self.tracker:
            if self.tracker.is_paused:
                self.tracker.resume()
                sender.title = 'Pause Tracking'
                self.menu['Status: Running'].title = 'Status: Running'
                rumps.notification("Activity Tracker", "", "Tracking resumed")
            else:
                self.tracker.pause()
                sender.title = 'Resume Tracking'
                self.menu['Status: Running'].title = 'Status: Paused'
                rumps.notification("Activity Tracker", "", "Tracking paused")

    @rumps.clicked('Quit')
    def quit_app(self, sender=None):
        """Quit the application, saving all data."""
        # Stop the update timer to prevent resource leak
        if self._timer:
            try:
                self._timer.stop()
            except Exception:
                pass

        if self.tracker:
            try:
                self.tracker.stop()
                rumps.notification(
                    "Activity Tracker",
                    "Stopped",
                    "All data has been saved"
                )
            except Exception as e:
                print(f"Error stopping tracker: {e}")

        rumps.quit_application()


def run_menu_bar(tracker_controller=None):
    """Run the menu bar application."""
    if not RUMPS_AVAILABLE:
        print("Menu bar integration not available. Install rumps: pip install rumps")
        return

    app = ActivityTrackerMenuBar(tracker_controller)
    app.run()
