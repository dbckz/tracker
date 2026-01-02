# Mac Activity Tracker

A comprehensive, privacy-focused activity tracking application for macOS that runs **entirely locally**. Monitor your computer usage, analyze productivity patterns, and gain insights into how you spend your time.

## Features

### Activity Tracking
- **Application Usage** - Track time spent in each app with automatic detection
- **Website Monitoring** - Monitor browsing activity across Safari, Chrome, Firefox, Arc, and other browsers
- **Typing Analytics** - Count words typed and calculate words-per-minute (WPM)

### Analytics & Insights
- **Productivity Scoring** - Daily productivity score (0-100) based on your app usage
- **Hourly Breakdown** - See when you're most active and productive
- **Weekly Trends** - Track patterns over time
- **Smart Recommendations** - Personalized tips based on your usage

### Privacy First
- 🔒 **100% Local** - All data stored on your machine in SQLite
- 🚫 **No Cloud** - Nothing leaves your computer
- 🗑️ **Your Data** - Delete anytime, export when needed

## Screenshots

The dashboard provides rich visualizations:
- Doughnut charts for app and website usage
- Line/bar charts for typing activity by hour
- Weekly trend analysis
- Productivity scores with actionable feedback

## Installation

### Prerequisites
- macOS 10.15 or later
- Python 3.9 or later

### Quick Install

```bash
# Clone or download the repository
cd tracker

# Run the installation script
chmod +x install.sh
./install.sh
```

### Manual Install

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the tracker
python main.py
```

## Usage

### Start Tracking

```bash
# Activate virtual environment
source venv/bin/activate

# Start with web dashboard (opens browser)
python main.py

# Start with menu bar icon
python main.py --menu-bar

# View-only mode (no tracking, just view data)
python main.py --dashboard

# Custom port
python main.py --port 8080
```

### Dashboard

Access the dashboard at `http://127.0.0.1:5050` (default)

The dashboard shows:
- Today's productivity score
- App usage breakdown
- Website time distribution
- Typing statistics
- Weekly trends
- Personalized recommendations

### API Endpoints

The tracker exposes a REST API for custom integrations:

```
GET /api/today          - Today's overview
GET /api/daily/YYYY-MM-DD - Specific date data
GET /api/weekly         - Weekly trends
GET /api/apps/today     - App usage
GET /api/websites/today - Website usage
GET /api/typing/today   - Typing stats
GET /api/recommendations - Personalized tips
GET /api/export?start=YYYY-MM-DD&end=YYYY-MM-DD - Export data
```

## Permissions

### Required: Accessibility

For typing tracking to work, you must grant Accessibility permissions:

1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Select **Accessibility** from the left sidebar
3. Click the lock to make changes
4. Add **Terminal.app** (or your terminal/IDE)

### Optional: Automation

For browser URL tracking in Safari:

1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Select **Automation** from the left sidebar
3. Allow the tracker to control Safari

## Data Storage

All data is stored in:
```
~/.mac_activity_tracker/
├── activity.db      # SQLite database
├── tracker.log      # Application logs
└── tracker.error.log
```

### Database Schema

- `app_activity` - Application usage sessions
- `website_activity` - Website visit sessions
- `typing_activity` - Hourly typing statistics
- `daily_summary` - Pre-computed daily summaries
- `hourly_summary` - Hourly breakdowns

## Autostart

The installation script can set up automatic startup. Alternatively:

### Manual LaunchAgent Setup

Create `~/Library/LaunchAgents/com.local.activitytracker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.activitytracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/main.py</string>
        <string>--menu-bar</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.local.activitytracker.plist
```

## Troubleshooting

### "Failed to create event tap"
You need to grant Accessibility permissions. See the Permissions section above.

### No browser URLs detected
- Chrome/Arc: Should work automatically
- Safari: Requires Automation permission
- Firefox: Uses history database (slight delay)

### Dashboard not loading
Check if the tracker is running:
```bash
curl http://127.0.0.1:5050/api/status
```

## Development

### Project Structure

```
tracker/
├── main.py              # Entry point
├── src/
│   ├── database.py      # SQLite models & queries
│   ├── tracker.py       # Main controller
│   ├── menu_bar.py      # Menu bar integration
│   ├── trackers/
│   │   ├── app_tracker.py     # App monitoring
│   │   ├── browser_tracker.py # URL tracking
│   │   └── typing_tracker.py  # Keystroke counting
│   ├── analytics/
│   │   └── analyzer.py  # Data analysis
│   └── web/
│       ├── app.py       # Flask dashboard
│       ├── templates/   # HTML templates
│       └── static/      # CSS & JS
├── requirements.txt
├── setup.py
└── install.sh
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/
```

## License

MIT License - see LICENSE file

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Privacy Note**: This application is designed to help you understand your own computer usage. All data remains on your local machine. No data is ever transmitted to external servers.
