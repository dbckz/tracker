"""
Analytics Engine for Mac Activity Tracker.
Processes collected data and generates insights, reports, and recommendations.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

from ..database import Database, AppActivity, WebsiteActivity, TypingActivity, DailySummary


class ActivityAnalyzer:
    """Analyzes activity data and generates insights."""

    def __init__(self, db: Database):
        self.db = db

    def get_app_summary_for_date(self, target_date: date) -> Dict:
        """Get summarized app usage for a specific date."""
        session = self.db.get_session()
        try:
            activities = session.query(AppActivity).filter_by(date=target_date).all()

            app_times = defaultdict(float)
            for activity in activities:
                app_times[activity.app_name] += activity.duration_seconds or 0

            total_time = sum(app_times.values())
            sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)

            return {
                'date': target_date.isoformat(),
                'total_seconds': total_time,
                'total_hours': round(total_time / 3600, 2),
                'app_count': len(app_times),
                'apps': [
                    {
                        'name': name,
                        'seconds': round(seconds, 1),
                        'hours': round(seconds / 3600, 2),
                        'percentage': round((seconds / total_time * 100) if total_time > 0 else 0, 1)
                    }
                    for name, seconds in sorted_apps
                ],
                'top_app': sorted_apps[0][0] if sorted_apps else None,
                'top_app_hours': round(sorted_apps[0][1] / 3600, 2) if sorted_apps else 0
            }
        finally:
            self.db.close_session()

    def get_website_summary_for_date(self, target_date: date) -> Dict:
        """Get summarized website usage for a specific date."""
        session = self.db.get_session()
        try:
            activities = session.query(WebsiteActivity).filter_by(date=target_date).all()

            domain_times = defaultdict(float)
            for activity in activities:
                if activity.domain:
                    domain_times[activity.domain] += activity.duration_seconds or 0

            total_time = sum(domain_times.values())
            sorted_domains = sorted(domain_times.items(), key=lambda x: x[1], reverse=True)

            return {
                'date': target_date.isoformat(),
                'total_seconds': total_time,
                'total_hours': round(total_time / 3600, 2),
                'domain_count': len(domain_times),
                'domains': [
                    {
                        'domain': domain,
                        'seconds': round(seconds, 1),
                        'hours': round(seconds / 3600, 2),
                        'percentage': round((seconds / total_time * 100) if total_time > 0 else 0, 1)
                    }
                    for domain, seconds in sorted_domains
                ],
                'top_domain': sorted_domains[0][0] if sorted_domains else None,
                'top_domain_hours': round(sorted_domains[0][1] / 3600, 2) if sorted_domains else 0
            }
        finally:
            self.db.close_session()

    def get_typing_summary_for_date(self, target_date: date) -> Dict:
        """Get typing statistics for a specific date."""
        session = self.db.get_session()
        try:
            activities = session.query(TypingActivity).filter_by(date=target_date).all()

            total_keystrokes = sum(a.keystrokes for a in activities)
            total_words = sum(a.words for a in activities)

            # Calculate hourly breakdown
            hourly_data = defaultdict(lambda: {'keystrokes': 0, 'words': 0})
            for activity in activities:
                hourly_data[activity.hour]['keystrokes'] += activity.keystrokes
                hourly_data[activity.hour]['words'] += activity.words

            # Find peak hours
            peak_hour = max(hourly_data.items(), key=lambda x: x[1]['keystrokes'])[0] if hourly_data else None

            # Calculate WPM (assuming about 8 hours of active work)
            active_hours = len([h for h in hourly_data if hourly_data[h]['keystrokes'] > 0])
            avg_wpm = round(total_words / (active_hours * 60) if active_hours > 0 else 0, 1)

            return {
                'date': target_date.isoformat(),
                'total_keystrokes': total_keystrokes,
                'total_words': total_words,
                'average_wpm': avg_wpm,
                'active_hours': active_hours,
                'peak_hour': peak_hour,
                'hourly_breakdown': dict(hourly_data)
            }
        finally:
            self.db.close_session()

    def get_daily_overview(self, target_date: date) -> Dict:
        """Get complete daily overview combining all metrics."""
        app_summary = self.get_app_summary_for_date(target_date)
        web_summary = self.get_website_summary_for_date(target_date)
        typing_summary = self.get_typing_summary_for_date(target_date)

        return {
            'date': target_date.isoformat(),
            'apps': app_summary,
            'websites': web_summary,
            'typing': typing_summary,
            'highlights': self._generate_daily_highlights(app_summary, web_summary, typing_summary)
        }

    def _generate_daily_highlights(self, app_summary: Dict, web_summary: Dict, typing_summary: Dict) -> List[str]:
        """Generate human-readable highlights for the day."""
        highlights = []

        total_hours = app_summary.get('total_hours', 0)
        if total_hours > 0:
            highlights.append(f"You were active on your computer for {total_hours:.1f} hours")

        top_app = app_summary.get('top_app')
        top_app_hours = app_summary.get('top_app_hours', 0)
        if top_app and top_app_hours > 0:
            highlights.append(f"Most used app: {top_app} ({top_app_hours:.1f} hours)")

        top_domain = web_summary.get('top_domain')
        top_domain_hours = web_summary.get('top_domain_hours', 0)
        if top_domain and top_domain_hours > 0:
            highlights.append(f"Most visited site: {top_domain} ({top_domain_hours:.1f} hours)")

        total_words = typing_summary.get('total_words', 0)
        avg_wpm = typing_summary.get('average_wpm', 0)
        if total_words > 0:
            highlights.append(f"You typed {total_words:,} words at an average of {avg_wpm:.0f} WPM")

        return highlights

    def get_weekly_trends(self, end_date: date = None) -> Dict:
        """Get trends for the past 7 days."""
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=6)
        days_data = []

        current = start_date
        while current <= end_date:
            days_data.append({
                'date': current.isoformat(),
                'apps': self.get_app_summary_for_date(current),
                'websites': self.get_website_summary_for_date(current),
                'typing': self.get_typing_summary_for_date(current)
            })
            current += timedelta(days=1)

        # Calculate trends
        total_hours_list = [d['apps']['total_hours'] for d in days_data]
        words_list = [d['typing']['total_words'] for d in days_data]

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days_data,
            'totals': {
                'total_hours': sum(total_hours_list),
                'avg_daily_hours': round(statistics.mean(total_hours_list), 2) if total_hours_list else 0,
                'total_words': sum(words_list),
                'avg_daily_words': round(statistics.mean(words_list)) if words_list else 0
            },
            'most_productive_day': self._find_most_productive_day(days_data),
            'insights': self._generate_weekly_insights(days_data)
        }

    def _find_most_productive_day(self, days_data: List[Dict]) -> Optional[str]:
        """Find the most productive day based on activity metrics."""
        if not days_data:
            return None

        # Score based on combination of active time and typing
        scored = []
        for day in days_data:
            score = (day['apps']['total_hours'] * 0.5 +
                    day['typing']['total_words'] / 1000 * 0.5)
            scored.append((day['date'], score))

        best = max(scored, key=lambda x: x[1])
        return best[0] if best[1] > 0 else None

    def _generate_weekly_insights(self, days_data: List[Dict]) -> List[str]:
        """Generate insights from weekly data."""
        insights = []

        # App usage patterns
        all_apps = defaultdict(float)
        for day in days_data:
            for app in day['apps'].get('apps', []):
                all_apps[app['name']] += app['seconds']

        top_apps = sorted(all_apps.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_apps:
            insights.append(f"Your top 5 apps this week: {', '.join(a[0] for a in top_apps)}")

        # Website patterns
        all_domains = defaultdict(float)
        for day in days_data:
            for domain in day['websites'].get('domains', []):
                all_domains[domain['domain']] += domain['seconds']

        top_domains = sorted(all_domains.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_domains:
            insights.append(f"Most visited sites: {', '.join(d[0] for d in top_domains)}")

        # Typing trends
        words_by_day = [d['typing']['total_words'] for d in days_data]
        if len(words_by_day) >= 3:
            recent_avg = statistics.mean(words_by_day[-3:])
            earlier_avg = statistics.mean(words_by_day[:-3]) if len(words_by_day) > 3 else recent_avg

            if recent_avg > earlier_avg * 1.2:
                insights.append("Your typing activity has increased recently!")
            elif recent_avg < earlier_avg * 0.8:
                insights.append("Your typing activity has decreased recently.")

        return insights

    def generate_productivity_score(self, target_date: date) -> Dict:
        """Generate a productivity score for a given day."""
        app_summary = self.get_app_summary_for_date(target_date)
        typing_summary = self.get_typing_summary_for_date(target_date)

        # Define productive vs unproductive apps/sites
        productive_apps = {
            'code', 'terminal', 'iterm', 'visual studio', 'xcode', 'intellij',
            'pycharm', 'webstorm', 'sublime', 'atom', 'vim', 'emacs',
            'notion', 'obsidian', 'notes', 'word', 'excel', 'powerpoint',
            'pages', 'numbers', 'keynote', 'figma', 'sketch', 'photoshop',
            'illustrator', 'slack', 'teams', 'zoom', 'mail', 'calendar'
        }

        distraction_apps = {
            'twitter', 'facebook', 'instagram', 'tiktok', 'reddit',
            'youtube', 'netflix', 'spotify', 'discord', 'messages'
        }

        productive_time = 0
        distraction_time = 0
        total_time = app_summary.get('total_seconds', 0)

        for app in app_summary.get('apps', []):
            app_name_lower = app['name'].lower()
            if any(prod in app_name_lower for prod in productive_apps):
                productive_time += app['seconds']
            elif any(dist in app_name_lower for dist in distraction_apps):
                distraction_time += app['seconds']

        # Calculate score (0-100)
        if total_time > 0:
            productive_ratio = productive_time / total_time
            distraction_ratio = distraction_time / total_time
            base_score = (productive_ratio * 100) - (distraction_ratio * 50)
            score = max(0, min(100, base_score))
        else:
            score = 0

        # Typing bonus
        words = typing_summary.get('total_words', 0)
        if words > 2000:
            score = min(100, score + 10)
        elif words > 1000:
            score = min(100, score + 5)

        return {
            'date': target_date.isoformat(),
            'score': round(score),
            'productive_hours': round(productive_time / 3600, 2),
            'distraction_hours': round(distraction_time / 3600, 2),
            'total_hours': round(total_time / 3600, 2),
            'grade': self._score_to_grade(score),
            'feedback': self._generate_productivity_feedback(score, productive_time, distraction_time, words)
        }

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_productivity_feedback(self, score: float, productive_time: float,
                                        distraction_time: float, words: int) -> List[str]:
        """Generate actionable feedback based on productivity metrics."""
        feedback = []

        if score >= 80:
            feedback.append("Great job! You had a highly productive day.")
        elif score >= 60:
            feedback.append("Decent productivity. There's room for improvement.")
        else:
            feedback.append("Consider reducing distractions to boost productivity.")

        if distraction_time > 3600:  # More than 1 hour of distractions
            hours = distraction_time / 3600
            feedback.append(f"You spent {hours:.1f} hours on distracting apps. Try setting time limits.")

        if productive_time < 3600 and distraction_time > productive_time:
            feedback.append("Tip: Try the Pomodoro technique - 25 mins work, 5 mins break.")

        if words < 100:
            feedback.append("Low typing activity detected. Was today a meeting-heavy day?")

        return feedback

    def get_recommendations(self) -> List[Dict]:
        """Generate personalized recommendations based on usage patterns."""
        today = date.today()
        weekly = self.get_weekly_trends(today)

        recommendations = []

        # Analyze patterns
        avg_hours = weekly['totals'].get('avg_daily_hours', 0)
        avg_words = weekly['totals'].get('avg_daily_words', 0)

        if avg_hours > 10:
            recommendations.append({
                'type': 'health',
                'priority': 'high',
                'title': 'Take more breaks',
                'description': f'You average {avg_hours:.1f} hours/day on your computer. '
                              'Consider taking regular breaks to prevent eye strain and fatigue.'
            })

        if avg_hours < 4:
            recommendations.append({
                'type': 'info',
                'priority': 'low',
                'title': 'Limited data',
                'description': 'Your daily computer usage is quite low. '
                              'This tracker works best with regular computer use.'
            })

        # App diversity
        all_apps = set()
        for day in weekly.get('days', []):
            for app in day['apps'].get('apps', []):
                all_apps.add(app['name'])

        if len(all_apps) < 3:
            recommendations.append({
                'type': 'productivity',
                'priority': 'medium',
                'title': 'Limited app usage',
                'description': 'You use very few applications. Consider exploring tools '
                              'that could enhance your workflow.'
            })

        return recommendations

    def export_data(self, start_date: date, end_date: date, format: str = 'json') -> Dict:
        """Export activity data for a date range."""
        data = {
            'export_date': datetime.now().isoformat(),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'daily_summaries': []
        }

        current = start_date
        while current <= end_date:
            data['daily_summaries'].append(self.get_daily_overview(current))
            current += timedelta(days=1)

        return data
