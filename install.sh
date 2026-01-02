#!/bin/bash
#
# Mac Activity Tracker - Installation Script
#
# This script:
# 1. Creates a virtual environment
# 2. Installs dependencies
# 3. Optionally sets up autostart via LaunchAgent
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
PLIST_NAME="com.local.activitytracker"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "=============================================="
echo "  Mac Activity Tracker - Installation"
echo "=============================================="
echo

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Install it from https://python.org or via Homebrew: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
echo
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo
echo "Installing dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo
echo "=============================================="
echo "  Installation Complete!"
echo "=============================================="
echo
echo "To start the tracker:"
echo "  cd $SCRIPT_DIR"
echo "  source venv/bin/activate"
echo "  python main.py"
echo
echo "Options:"
echo "  python main.py              # Start with dashboard"
echo "  python main.py --menu-bar   # Start with menu bar icon"
echo "  python main.py --dashboard  # View-only mode"
echo

# Ask about autostart
read -p "Would you like to set up autostart on login? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting up LaunchAgent..."

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"

    # Create the plist file
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>$SCRIPT_DIR/main.py</string>
        <string>--menu-bar</string>
        <string>--no-browser</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$HOME/.mac_activity_tracker/tracker.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.mac_activity_tracker/tracker.error.log</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
</dict>
</plist>
EOF

    # Load the LaunchAgent
    launchctl load "$PLIST_PATH" 2>/dev/null || true

    echo
    echo "Autostart configured!"
    echo "The tracker will start automatically on login."
    echo
    echo "To disable autostart:"
    echo "  launchctl unload $PLIST_PATH"
    echo
fi

echo "=============================================="
echo "  IMPORTANT: Accessibility Permissions"
echo "=============================================="
echo
echo "For typing tracking to work, you need to grant"
echo "Accessibility permissions to Terminal or your IDE."
echo
echo "Go to: System Preferences > Security & Privacy"
echo "       > Privacy > Accessibility"
echo
echo "Add Terminal.app or your terminal application."
echo "=============================================="
