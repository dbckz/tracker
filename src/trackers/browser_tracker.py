"""
Browser/Website Activity Tracker for macOS.
Extracts URLs and tracks time spent on different websites.
"""

import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List
from urllib.parse import urlparse

# macOS specific imports
try:
    from AppKit import NSWorkspace
    from ScriptingBridge import SBApplication
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False

from .app_tracker import BROWSER_BUNDLE_IDS, is_browser


class BrowserTracker:
    """Tracks website activity across different browsers."""

    def __init__(self, on_site_change: Optional[Callable] = None, poll_interval: float = 2.0):
        """
        Initialize the browser tracker.

        Args:
            on_site_change: Callback when active website changes.
                           Receives (old_site_info, new_site_info, duration_seconds)
            poll_interval: How often to check for site changes (seconds)
        """
        self.on_site_change = on_site_change
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Current site tracking
        self._current_url = None
        self._current_domain = None
        self._current_title = None
        self._current_browser = None
        self._site_start_time = None

        # Statistics
        self.total_site_changes = 0
        self.domains_visited: Dict[str, float] = {}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ''
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove 'www.' prefix for consistency
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.lower()
        except Exception:
            return ''

    def _get_safari_url(self) -> tuple:
        """Get current URL and title from Safari using ScriptingBridge."""
        if not MACOS_AVAILABLE:
            return None, None

        try:
            safari = SBApplication.applicationWithBundleIdentifier_("com.apple.Safari")
            if safari and safari.windows() and len(safari.windows()) > 0:
                window = safari.windows()[0]
                if window.currentTab():
                    tab = window.currentTab()
                    url = tab.URL()
                    title = tab.name()
                    return url, title
        except Exception:
            pass
        return None, None

    def _get_chrome_url(self) -> tuple:
        """Get current URL and title from Chrome using ScriptingBridge."""
        if not MACOS_AVAILABLE:
            return None, None

        try:
            chrome = SBApplication.applicationWithBundleIdentifier_("com.google.Chrome")
            if chrome and chrome.windows() and len(chrome.windows()) > 0:
                window = chrome.windows()[0]
                if window.activeTab():
                    tab = window.activeTab()
                    url = tab.URL()
                    title = tab.title()
                    return url, title
        except Exception:
            pass
        return None, None

    def _get_firefox_url_from_history(self) -> tuple:
        """Get recent Firefox URL from history database."""
        # Firefox stores history in places.sqlite
        firefox_profile = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")

        if not os.path.exists(firefox_profile):
            return None, None

        try:
            # Find the default profile
            profiles = [d for d in os.listdir(firefox_profile) if d.endswith('.default') or 'default' in d.lower()]
            if not profiles:
                profiles = os.listdir(firefox_profile)

            for profile in profiles:
                places_db = os.path.join(firefox_profile, profile, "places.sqlite")
                if os.path.exists(places_db):
                    # Copy to temp to avoid locking issues
                    import shutil
                    temp_db = "/tmp/firefox_places_temp.sqlite"
                    shutil.copy2(places_db, temp_db)

                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()

                    # Get most recent visit
                    cursor.execute("""
                        SELECT p.url, p.title
                        FROM moz_places p
                        JOIN moz_historyvisits h ON p.id = h.place_id
                        ORDER BY h.visit_date DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    conn.close()

                    if result:
                        return result[0], result[1]
        except Exception:
            pass

        return None, None

    def _get_arc_url(self) -> tuple:
        """Get current URL and title from Arc browser."""
        if not MACOS_AVAILABLE:
            return None, None

        try:
            arc = SBApplication.applicationWithBundleIdentifier_("company.thebrowser.Browser")
            if arc and arc.windows() and len(arc.windows()) > 0:
                window = arc.windows()[0]
                if hasattr(window, 'activeTab') and window.activeTab():
                    tab = window.activeTab()
                    url = tab.URL() if hasattr(tab, 'URL') else None
                    title = tab.title() if hasattr(tab, 'title') else None
                    return url, title
        except Exception:
            pass
        return None, None

    def _get_brave_url(self) -> tuple:
        """Get current URL and title from Brave (Chromium-based)."""
        if not MACOS_AVAILABLE:
            return None, None

        try:
            brave = SBApplication.applicationWithBundleIdentifier_("com.brave.Browser")
            if brave and brave.windows() and len(brave.windows()) > 0:
                window = brave.windows()[0]
                if hasattr(window, 'activeTab') and window.activeTab():
                    tab = window.activeTab()
                    url = tab.URL() if hasattr(tab, 'URL') else None
                    title = tab.title() if hasattr(tab, 'title') else None
                    return url, title
        except Exception:
            pass
        return None, None

    def _get_current_browser_url(self, bundle_id: str) -> tuple:
        """Get URL from the active browser based on bundle ID."""
        url_getters = {
            'com.apple.Safari': self._get_safari_url,
            'com.google.Chrome': self._get_chrome_url,
            'org.mozilla.firefox': self._get_firefox_url_from_history,
            'company.thebrowser.Browser': self._get_arc_url,
            'com.brave.Browser': self._get_brave_url,
        }

        getter = url_getters.get(bundle_id)
        if getter:
            return getter()

        # For other Chromium-based browsers, try Chrome-like API
        if bundle_id in ['com.microsoft.edgemac', 'com.operasoftware.Opera', 'com.vivaldi.Vivaldi']:
            try:
                browser = SBApplication.applicationWithBundleIdentifier_(bundle_id)
                if browser and browser.windows() and len(browser.windows()) > 0:
                    window = browser.windows()[0]
                    if hasattr(window, 'activeTab') and window.activeTab():
                        tab = window.activeTab()
                        url = tab.URL() if hasattr(tab, 'URL') else None
                        title = tab.title() if hasattr(tab, 'title') else None
                        return url, title
            except Exception:
                pass

        return None, None

    def _get_active_browser_info(self) -> Optional[dict]:
        """Get information about the currently active browser tab."""
        if not MACOS_AVAILABLE:
            return None

        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.activeApplication() or workspace.frontmostApplication()

        if not active_app:
            return None

        bundle_id = active_app.get('NSApplicationBundleIdentifier', '')

        if not is_browser(bundle_id):
            return None

        browser_name = BROWSER_BUNDLE_IDS.get(bundle_id, 'Unknown Browser')
        url, title = self._get_current_browser_url(bundle_id)

        if url:
            return {
                'url': url,
                'domain': self._extract_domain(url),
                'title': title or '',
                'browser': browser_name,
                'bundle_id': bundle_id
            }

        return None

    def _tracking_loop(self):
        """Main tracking loop for browser activity."""
        while self._running:
            try:
                browser_info = self._get_active_browser_info()
                current_time = datetime.now()

                if browser_info:
                    # Check if site/URL changed
                    if browser_info['url'] != self._current_url:
                        # Record previous site
                        if self._current_url and self._site_start_time:
                            duration = (current_time - self._site_start_time).total_seconds()

                            old_site_info = {
                                'url': self._current_url,
                                'domain': self._current_domain,
                                'title': self._current_title,
                                'browser': self._current_browser,
                                'start_time': self._site_start_time,
                                'end_time': current_time,
                                'duration_seconds': duration
                            }

                            # Update domain stats
                            if self._current_domain:
                                self.domains_visited[self._current_domain] = \
                                    self.domains_visited.get(self._current_domain, 0) + duration

                            if self.on_site_change:
                                self.on_site_change(old_site_info, browser_info, duration)

                            self.total_site_changes += 1

                        # Update current site
                        self._current_url = browser_info['url']
                        self._current_domain = browser_info['domain']
                        self._current_title = browser_info['title']
                        self._current_browser = browser_info['browser']
                        self._site_start_time = current_time

                else:
                    # Not in a browser - close current session if any
                    if self._current_url and self._site_start_time:
                        duration = (current_time - self._site_start_time).total_seconds()

                        old_site_info = {
                            'url': self._current_url,
                            'domain': self._current_domain,
                            'title': self._current_title,
                            'browser': self._current_browser,
                            'start_time': self._site_start_time,
                            'end_time': current_time,
                            'duration_seconds': duration
                        }

                        if self._current_domain:
                            self.domains_visited[self._current_domain] = \
                                self.domains_visited.get(self._current_domain, 0) + duration

                        if self.on_site_change:
                            self.on_site_change(old_site_info, None, duration)

                        self._current_url = None
                        self._current_domain = None
                        self._current_title = None
                        self._current_browser = None
                        self._site_start_time = None

            except Exception as e:
                print(f"Error in browser tracking loop: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start tracking browser activity."""
        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()

        print("Browser tracking started.")

    def stop(self) -> dict:
        """Stop tracking and return statistics."""
        if not self._running:
            return {}

        self._running = False

        # Record final site if any
        if self._current_url and self._site_start_time:
            end_time = datetime.now()
            duration = (end_time - self._site_start_time).total_seconds()

            if self._current_domain:
                self.domains_visited[self._current_domain] = \
                    self.domains_visited.get(self._current_domain, 0) + duration

            if self.on_site_change:
                final_site_info = {
                    'url': self._current_url,
                    'domain': self._current_domain,
                    'title': self._current_title,
                    'browser': self._current_browser,
                    'start_time': self._site_start_time,
                    'end_time': end_time,
                    'duration_seconds': duration
                }
                self.on_site_change(final_site_info, None, duration)

        if self._thread:
            self._thread.join(timeout=2.0)

        return {
            'total_site_changes': self.total_site_changes,
            'domains_visited': self.domains_visited,
            'top_domains': sorted(self.domains_visited.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def get_current_site(self) -> Optional[dict]:
        """Get information about the currently tracked website."""
        if not self._current_url:
            return self._get_active_browser_info()

        current_time = datetime.now()
        duration = (current_time - self._site_start_time).total_seconds() if self._site_start_time else 0

        return {
            'url': self._current_url,
            'domain': self._current_domain,
            'title': self._current_title,
            'browser': self._current_browser,
            'start_time': self._site_start_time,
            'current_duration': duration
        }

    @property
    def is_running(self) -> bool:
        """Check if tracker is currently running."""
        return self._running


def categorize_domain(domain: str) -> str:
    """Categorize a domain into common categories."""
    categories = {
        'social': ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'linkedin.com',
                   'reddit.com', 'tiktok.com', 'snapchat.com', 'pinterest.com', 'threads.net'],
        'video': ['youtube.com', 'netflix.com', 'twitch.tv', 'vimeo.com', 'hulu.com',
                  'disneyplus.com', 'primevideo.com', 'hbomax.com'],
        'productivity': ['notion.so', 'trello.com', 'asana.com', 'monday.com', 'clickup.com',
                        'todoist.com', 'evernote.com', 'docs.google.com', 'sheets.google.com'],
        'development': ['github.com', 'gitlab.com', 'stackoverflow.com', 'bitbucket.org',
                       'npmjs.com', 'pypi.org', 'docs.python.org', 'developer.mozilla.org'],
        'communication': ['gmail.com', 'mail.google.com', 'outlook.com', 'slack.com',
                         'discord.com', 'zoom.us', 'teams.microsoft.com', 'meet.google.com'],
        'shopping': ['amazon.com', 'ebay.com', 'walmart.com', 'target.com', 'etsy.com'],
        'news': ['news.google.com', 'cnn.com', 'bbc.com', 'nytimes.com', 'reddit.com/r/news'],
        'search': ['google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com'],
    }

    domain = domain.lower()
    for category, domains in categories.items():
        for d in domains:
            if domain == d or domain.endswith('.' + d):
                return category

    return 'other'
