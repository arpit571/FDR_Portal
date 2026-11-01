"""
Date utilities — respects DEMO_DATE override for hackathon demo
"""
from datetime import date, datetime
from src.config.settings import get_settings


def today() -> date:
    """Return current date, respecting DEMO_DATE override."""
    settings = get_settings()
    if settings.DEMO_DATE:
        try:
            return date.fromisoformat(settings.DEMO_DATE)
        except ValueError:
            pass
    return date.today()


def now() -> datetime:
    """Return current datetime, respecting DEMO_DATE override."""
    settings = get_settings()
    if settings.DEMO_DATE:
        try:
            demo = date.fromisoformat(settings.DEMO_DATE)
            return datetime(demo.year, demo.month, demo.day,
                            datetime.now().hour, datetime.now().minute,
                            datetime.now().second)
        except ValueError:
            pass
    return datetime.now()


def days_until(target: date) -> int:
    """Days from today until target (negative if past)."""
    return (target - today()).days
