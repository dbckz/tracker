"""
Flask Web Dashboard for Mac Activity Tracker.
Provides a local web interface for viewing analytics and reports.
"""

import json
from datetime import date, datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from ..database import Database
from ..analytics.analyzer import ActivityAnalyzer


def create_app(db: Database = None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    CORS(app)

    # Initialize database and analyzer
    if db is None:
        db = Database()
    analyzer = ActivityAnalyzer(db)

    @app.route('/')
    def dashboard():
        """Main dashboard page."""
        return render_template('dashboard.html')

    @app.route('/api/today')
    def api_today():
        """Get today's activity summary."""
        today = date.today()
        overview = analyzer.get_daily_overview(today)
        productivity = analyzer.generate_productivity_score(today)
        return jsonify({
            'overview': overview,
            'productivity': productivity
        })

    @app.route('/api/daily/<date_str>')
    def api_daily(date_str):
        """Get activity for a specific date."""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            overview = analyzer.get_daily_overview(target_date)
            productivity = analyzer.generate_productivity_score(target_date)
            return jsonify({
                'overview': overview,
                'productivity': productivity
            })
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    @app.route('/api/weekly')
    def api_weekly():
        """Get weekly trends and insights."""
        end_date = date.today()
        if 'end_date' in request.args:
            try:
                end_date = datetime.strptime(request.args['end_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        trends = analyzer.get_weekly_trends(end_date)
        return jsonify(trends)

    @app.route('/api/apps/today')
    def api_apps_today():
        """Get today's app usage."""
        today = date.today()
        summary = analyzer.get_app_summary_for_date(today)
        return jsonify(summary)

    @app.route('/api/apps/<date_str>')
    def api_apps_date(date_str):
        """Get app usage for a specific date."""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            summary = analyzer.get_app_summary_for_date(target_date)
            return jsonify(summary)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

    @app.route('/api/websites/today')
    def api_websites_today():
        """Get today's website usage."""
        today = date.today()
        summary = analyzer.get_website_summary_for_date(today)
        return jsonify(summary)

    @app.route('/api/websites/<date_str>')
    def api_websites_date(date_str):
        """Get website usage for a specific date."""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            summary = analyzer.get_website_summary_for_date(target_date)
            return jsonify(summary)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

    @app.route('/api/typing/today')
    def api_typing_today():
        """Get today's typing statistics."""
        today = date.today()
        summary = analyzer.get_typing_summary_for_date(today)
        return jsonify(summary)

    @app.route('/api/typing/<date_str>')
    def api_typing_date(date_str):
        """Get typing statistics for a specific date."""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            summary = analyzer.get_typing_summary_for_date(target_date)
            return jsonify(summary)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

    @app.route('/api/recommendations')
    def api_recommendations():
        """Get personalized recommendations."""
        recommendations = analyzer.get_recommendations()
        return jsonify({'recommendations': recommendations})

    @app.route('/api/export')
    def api_export():
        """Export data for a date range."""
        try:
            start = request.args.get('start', (date.today() - timedelta(days=7)).isoformat())
            end = request.args.get('end', date.today().isoformat())

            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()

            data = analyzer.export_data(start_date, end_date)
            return jsonify(data)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

    @app.route('/api/status')
    def api_status():
        """Get tracker status."""
        return jsonify({
            'status': 'running',
            'database': db.db_path,
            'timestamp': datetime.now().isoformat()
        })

    return app


def run_dashboard(host='127.0.0.1', port=5050, debug=False, db=None):
    """Run the dashboard server."""
    app = create_app(db)
    print(f"\n📊 Activity Dashboard running at http://{host}:{port}")
    print("Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
