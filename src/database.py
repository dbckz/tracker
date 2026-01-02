"""
Database layer for Mac Activity Tracker.
Uses SQLite for fully local storage.
"""

import os
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

Base = declarative_base()

# Default database path in user's home directory
DEFAULT_DB_PATH = os.path.expanduser("~/.mac_activity_tracker/activity.db")


class AppActivity(Base):
    """Tracks time spent in each application."""
    __tablename__ = 'app_activity'

    id = Column(Integer, primary_key=True)
    app_name = Column(String(255), nullable=False, index=True)
    app_bundle_id = Column(String(255))
    window_title = Column(Text)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_seconds = Column(Float, default=0)
    date = Column(Date, nullable=False, index=True)

    __table_args__ = (
        Index('idx_app_date', 'app_name', 'date'),
    )


class WebsiteActivity(Base):
    """Tracks websites visited (extracted from browser windows)."""
    __tablename__ = 'website_activity'

    id = Column(Integer, primary_key=True)
    url = Column(Text)
    domain = Column(String(255), index=True)
    page_title = Column(Text)
    browser = Column(String(100))
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_seconds = Column(Float, default=0)
    date = Column(Date, nullable=False, index=True)

    __table_args__ = (
        Index('idx_domain_date', 'domain', 'date'),
    )


class TypingActivity(Base):
    """Tracks typing statistics."""
    __tablename__ = 'typing_activity'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    keystrokes = Column(Integer, default=0)
    words = Column(Integer, default=0)
    app_name = Column(String(255))

    __table_args__ = (
        Index('idx_typing_date_hour', 'date', 'hour'),
    )


class DailySummary(Base):
    """Pre-computed daily summaries for faster querying."""
    __tablename__ = 'daily_summary'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    total_active_seconds = Column(Float, default=0)
    total_keystrokes = Column(Integer, default=0)
    total_words = Column(Integer, default=0)
    avg_wpm = Column(Float, default=0)
    top_app = Column(String(255))
    top_app_seconds = Column(Float, default=0)
    top_domain = Column(String(255))
    top_domain_seconds = Column(Float, default=0)
    app_count = Column(Integer, default=0)
    domain_count = Column(Integer, default=0)


class HourlySummary(Base):
    """Hourly breakdown for pattern analysis."""
    __tablename__ = 'hourly_summary'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    active_seconds = Column(Float, default=0)
    keystrokes = Column(Integer, default=0)
    words = Column(Integer, default=0)
    primary_app = Column(String(255))

    __table_args__ = (
        Index('idx_hourly_date_hour', 'date', 'hour', unique=True),
    )


class Database:
    """Database manager for activity tracking."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_directory()
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self._create_tables()

    def _ensure_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get a database session."""
        return self.Session()

    def close_session(self):
        """Close the current session."""
        self.Session.remove()

    # App Activity Methods
    def record_app_activity(self, app_name: str, app_bundle_id: str,
                           window_title: str, start_time: datetime,
                           end_time: datetime = None, duration_seconds: float = 0):
        """Record an app activity session."""
        session = self.get_session()
        try:
            activity = AppActivity(
                app_name=app_name,
                app_bundle_id=app_bundle_id,
                window_title=window_title,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                date=start_time.date()
            )
            session.add(activity)
            session.commit()
            return activity.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    def update_app_activity(self, activity_id: int, end_time: datetime, duration_seconds: float):
        """Update an existing app activity record."""
        session = self.get_session()
        try:
            activity = session.query(AppActivity).filter_by(id=activity_id).first()
            if activity:
                activity.end_time = end_time
                activity.duration_seconds = duration_seconds
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    # Website Activity Methods
    def record_website_activity(self, url: str, domain: str, page_title: str,
                                browser: str, start_time: datetime,
                                end_time: datetime = None, duration_seconds: float = 0):
        """Record a website visit."""
        session = self.get_session()
        try:
            activity = WebsiteActivity(
                url=url,
                domain=domain,
                page_title=page_title,
                browser=browser,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                date=start_time.date()
            )
            session.add(activity)
            session.commit()
            return activity.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    def update_website_activity(self, activity_id: int, end_time: datetime, duration_seconds: float):
        """Update an existing website activity record."""
        session = self.get_session()
        try:
            activity = session.query(WebsiteActivity).filter_by(id=activity_id).first()
            if activity:
                activity.end_time = end_time
                activity.duration_seconds = duration_seconds
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    # Typing Activity Methods
    def record_typing_activity(self, keystrokes: int, words: int, app_name: str = None):
        """Record typing statistics for the current moment."""
        session = self.get_session()
        try:
            now = datetime.now()
            activity = TypingActivity(
                timestamp=now,
                date=now.date(),
                hour=now.hour,
                keystrokes=keystrokes,
                words=words,
                app_name=app_name
            )
            session.add(activity)
            session.commit()
            return activity.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    def increment_typing_stats(self, keystrokes: int = 0, words: int = 0, app_name: str = None):
        """Increment typing stats for current hour (upsert pattern)."""
        session = self.get_session()
        try:
            now = datetime.now()
            today = now.date()
            current_hour = now.hour

            existing = session.query(TypingActivity).filter_by(
                date=today, hour=current_hour
            ).first()

            if existing:
                existing.keystrokes += keystrokes
                existing.words += words
                existing.timestamp = now
                if app_name:
                    existing.app_name = app_name
            else:
                activity = TypingActivity(
                    timestamp=now,
                    date=today,
                    hour=current_hour,
                    keystrokes=keystrokes,
                    words=words,
                    app_name=app_name
                )
                session.add(activity)

            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    # Query Methods
    def get_app_activity_for_date(self, target_date: date):
        """Get all app activity for a specific date."""
        session = self.get_session()
        try:
            return session.query(AppActivity).filter_by(date=target_date).all()
        finally:
            self.close_session()

    def get_website_activity_for_date(self, target_date: date):
        """Get all website activity for a specific date."""
        session = self.get_session()
        try:
            return session.query(WebsiteActivity).filter_by(date=target_date).all()
        finally:
            self.close_session()

    def get_typing_activity_for_date(self, target_date: date):
        """Get typing activity for a specific date."""
        session = self.get_session()
        try:
            return session.query(TypingActivity).filter_by(date=target_date).all()
        finally:
            self.close_session()

    def get_daily_summary(self, target_date: date):
        """Get or create daily summary."""
        session = self.get_session()
        try:
            return session.query(DailySummary).filter_by(date=target_date).first()
        finally:
            self.close_session()

    def save_daily_summary(self, summary_data: dict):
        """Save or update daily summary."""
        session = self.get_session()
        try:
            target_date = summary_data['date']
            existing = session.query(DailySummary).filter_by(date=target_date).first()

            if existing:
                for key, value in summary_data.items():
                    setattr(existing, key, value)
            else:
                summary = DailySummary(**summary_data)
                session.add(summary)

            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    def get_date_range_summaries(self, start_date: date, end_date: date):
        """Get daily summaries for a date range."""
        session = self.get_session()
        try:
            return session.query(DailySummary).filter(
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            ).order_by(DailySummary.date).all()
        finally:
            self.close_session()
