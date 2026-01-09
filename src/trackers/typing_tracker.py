"""
Typing/Keyboard Activity Tracker for macOS.
Monitors keystrokes and calculates typing statistics like WPM.

IMPORTANT: This requires Accessibility permissions to be granted to the terminal
or application running this script.
"""

import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Callable

# macOS specific imports
try:
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        CGEventMaskBit,
        kCGEventKeyDown,
        kCGHeadInsertEventTap,
        kCGSessionEventTap,
        CFMachPortCreateRunLoopSource,
        CFRunLoopAddSource,
        CFRunLoopGetCurrent,
        CFRunLoopRun,
        CFRunLoopStop,
        kCFRunLoopCommonModes,
        CGEventGetIntegerValueField,
        kCGKeyboardEventKeycode,
    )
    from AppKit import NSWorkspace
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    print("Warning: macOS frameworks not available. Typing tracking disabled.")


# Common word-ending keys (space, return, punctuation)
WORD_ENDING_KEYCODES = {
    49,  # Space
    36,  # Return
    76,  # Enter (numpad)
    48,  # Tab
    47,  # Period
    43,  # Comma
    41,  # Semicolon
    30,  # Right bracket
    33,  # Left bracket
    39,  # Quote
    42,  # Backslash
    44,  # Slash
}

# Keys to ignore in keystroke count (modifiers, function keys, etc.)
IGNORED_KEYCODES = {
    54, 55,  # Command keys
    56, 60,  # Shift keys
    58, 61,  # Option keys
    59, 62,  # Control keys
    57,      # Caps Lock
    63,      # Function key
    # Function keys F1-F12
    122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111,
    # Arrow keys
    123, 124, 125, 126,
    # Other special keys
    53,  # Escape
    117, # Delete (forward)
    51,  # Backspace
    115, # Home
    119, # End
    116, # Page Up
    121, # Page Down
}


class TypingTracker:
    """Tracks typing activity including keystrokes, words, and WPM."""

    def __init__(self, on_stats_update: Optional[Callable] = None,
                 wpm_window_seconds: int = 60,
                 stats_callback_interval: float = 10.0):
        """
        Initialize the typing tracker.

        Args:
            on_stats_update: Callback for periodic stats updates.
                           Receives (stats_dict)
            wpm_window_seconds: Time window for WPM calculation
            stats_callback_interval: How often to call stats callback (seconds)
        """
        self.on_stats_update = on_stats_update
        self.wpm_window_seconds = wpm_window_seconds
        self.stats_callback_interval = stats_callback_interval

        self._running = False
        self._event_tap = None
        self._run_loop_source = None
        self._thread: Optional[threading.Thread] = None
        self._stats_thread: Optional[threading.Thread] = None
        self._run_loop = None

        # Keystroke tracking - use maxlen to prevent unbounded memory growth
        # At 100 keystrokes/min, 2000 entries = ~20 minutes of history
        # This is more than enough for WPM calculation (default 60 second window)
        self._keystrokes = deque(maxlen=2000)  # (timestamp, keycode) for WPM calculation
        self._word_boundaries = deque(maxlen=500)  # timestamps of word completions

        # Statistics
        self.total_keystrokes = 0
        self.total_words = 0
        self.session_start = None

        # Thread safety
        self._lock = threading.Lock()

    def _key_event_callback(self, proxy, event_type, event, refcon):
        """Callback for keyboard events."""
        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            current_time = datetime.now()

            with self._lock:
                # Skip ignored keys
                if keycode not in IGNORED_KEYCODES:
                    self._keystrokes.append((current_time, keycode))
                    self.total_keystrokes += 1

                    # Check for word boundary
                    if keycode in WORD_ENDING_KEYCODES:
                        self._word_boundaries.append(current_time)
                        self.total_words += 1

                # Clean up old entries (older than window)
                cutoff = current_time - timedelta(seconds=self.wpm_window_seconds)
                while self._keystrokes and self._keystrokes[0][0] < cutoff:
                    self._keystrokes.popleft()
                while self._word_boundaries and self._word_boundaries[0] < cutoff:
                    self._word_boundaries.popleft()

        return event

    def _get_current_app(self) -> str:
        """Get the name of the currently active application."""
        if not MACOS_AVAILABLE:
            return "Unknown"

        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication() or workspace.frontmostApplication()
            if active_app:
                return active_app.get('NSApplicationName', 'Unknown')
        except Exception:
            pass
        return "Unknown"

    def _event_loop(self):
        """Run the event tap loop."""
        if not MACOS_AVAILABLE:
            return

        try:
            # Create event tap for key down events
            event_mask = CGEventMaskBit(kCGEventKeyDown)

            self._event_tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                0,  # Options (0 = default)
                event_mask,
                self._key_event_callback,
                None  # User info
            )

            if self._event_tap is None:
                print("ERROR: Failed to create event tap. Make sure Accessibility permissions are granted.")
                print("Go to System Preferences > Security & Privacy > Privacy > Accessibility")
                print("and add this application to the list.")
                self._running = False
                return

            # Create run loop source
            self._run_loop_source = CFMachPortCreateRunLoopSource(None, self._event_tap, 0)
            self._run_loop = CFRunLoopGetCurrent()

            CFRunLoopAddSource(self._run_loop, self._run_loop_source, kCFRunLoopCommonModes)
            CGEventTapEnable(self._event_tap, True)

            print("Typing tracking started. Listening for keyboard events...")

            # Run the loop
            CFRunLoopRun()

        except Exception as e:
            print(f"Error in event loop: {e}")
            self._running = False

    def _stats_loop(self):
        """Periodically calculate and report statistics."""
        while self._running:
            try:
                stats = self.get_current_stats()

                if self.on_stats_update:
                    self.on_stats_update(stats)

            except Exception as e:
                print(f"Error in stats loop: {e}")

            time.sleep(self.stats_callback_interval)

    def get_current_stats(self) -> dict:
        """Calculate current typing statistics."""
        current_time = datetime.now()

        with self._lock:
            # Keys in the window
            window_keystrokes = len(self._keystrokes)
            window_words = len(self._word_boundaries)

            # Calculate WPM
            if window_words > 0 and self._word_boundaries:
                # Time span of words in window
                first_word_time = self._word_boundaries[0]
                time_span_minutes = (current_time - first_word_time).total_seconds() / 60.0

                if time_span_minutes > 0:
                    wpm = window_words / time_span_minutes
                else:
                    wpm = 0
            else:
                wpm = 0

            # Calculate keys per minute
            if window_keystrokes > 0 and self._keystrokes:
                first_key_time = self._keystrokes[0][0]
                time_span_minutes = (current_time - first_key_time).total_seconds() / 60.0

                if time_span_minutes > 0:
                    kpm = window_keystrokes / time_span_minutes
                else:
                    kpm = 0
            else:
                kpm = 0

        # Session duration
        session_seconds = 0
        if self.session_start:
            session_seconds = (current_time - self.session_start).total_seconds()

        # Average characters per word (industry standard is ~5)
        avg_word_length = 5
        if self.total_words > 0 and self.total_keystrokes > 0:
            avg_word_length = self.total_keystrokes / self.total_words

        return {
            'timestamp': current_time,
            'current_app': self._get_current_app(),

            # Window statistics (last N seconds)
            'window_keystrokes': window_keystrokes,
            'window_words': window_words,
            'current_wpm': round(wpm, 1),
            'current_kpm': round(kpm, 1),
            'window_seconds': self.wpm_window_seconds,

            # Session totals
            'total_keystrokes': self.total_keystrokes,
            'total_words': self.total_words,
            'session_seconds': round(session_seconds, 1),

            # Averages
            'avg_word_length': round(avg_word_length, 1),
            'session_avg_wpm': round(self.total_words / (session_seconds / 60) if session_seconds > 0 else 0, 1),
        }

    def start(self):
        """Start tracking typing activity."""
        if self._running:
            return

        if not MACOS_AVAILABLE:
            print("Cannot start typing tracker: macOS frameworks not available.")
            return

        self._running = True
        self.session_start = datetime.now()

        # Start event loop thread
        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()

        # Start stats reporting thread
        self._stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        self._stats_thread.start()

    def stop(self) -> dict:
        """Stop tracking and return session statistics."""
        if not self._running:
            return {}

        self._running = False

        # Stop the run loop
        if self._run_loop:
            try:
                CFRunLoopStop(self._run_loop)
            except Exception:
                pass

        # Disable event tap
        if self._event_tap:
            try:
                CGEventTapEnable(self._event_tap, False)
            except Exception:
                pass

        # Wait for threads
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._stats_thread:
            self._stats_thread.join(timeout=2.0)

        # Final stats
        return self.get_current_stats()

    @property
    def is_running(self) -> bool:
        """Check if tracker is currently running."""
        return self._running


class TypingTrackerSimulated:
    """
    Simulated typing tracker for testing on non-macOS systems
    or when accessibility permissions aren't available.
    """

    def __init__(self, on_stats_update: Optional[Callable] = None,
                 wpm_window_seconds: int = 60,
                 stats_callback_interval: float = 10.0):
        self.on_stats_update = on_stats_update
        self.wpm_window_seconds = wpm_window_seconds
        self.stats_callback_interval = stats_callback_interval
        self._running = False
        self._thread = None

        self.total_keystrokes = 0
        self.total_words = 0
        self.session_start = None

    def _simulate_loop(self):
        """Simulate typing activity for testing."""
        import random
        while self._running:
            # Simulate some keystrokes
            keystrokes = random.randint(0, 50)
            words = random.randint(0, keystrokes // 5) if keystrokes > 0 else 0

            self.total_keystrokes += keystrokes
            self.total_words += words

            if self.on_stats_update:
                self.on_stats_update(self.get_current_stats())

            time.sleep(self.stats_callback_interval)

    def get_current_stats(self) -> dict:
        current_time = datetime.now()
        session_seconds = 0
        if self.session_start:
            session_seconds = (current_time - self.session_start).total_seconds()

        return {
            'timestamp': current_time,
            'current_app': 'Simulated',
            'window_keystrokes': 0,
            'window_words': 0,
            'current_wpm': 0,
            'current_kpm': 0,
            'window_seconds': self.wpm_window_seconds,
            'total_keystrokes': self.total_keystrokes,
            'total_words': self.total_words,
            'session_seconds': round(session_seconds, 1),
            'avg_word_length': 5.0,
            'session_avg_wpm': round(self.total_words / (session_seconds / 60) if session_seconds > 0 else 0, 1),
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self.session_start = datetime.now()
        self._thread = threading.Thread(target=self._simulate_loop, daemon=True)
        self._thread.start()
        print("Simulated typing tracking started.")

    def stop(self) -> dict:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        return self.get_current_stats()

    @property
    def is_running(self) -> bool:
        return self._running
