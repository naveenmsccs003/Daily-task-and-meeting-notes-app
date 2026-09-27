"""Centralized date handling so every module (dashboard, tasks, meetings,
reports, exports) shares one definition of "today", "this week", etc.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

DATE_FMT = "%Y-%m-%d"
DISPLAY_FMT = "%d %b %Y"

VALID_PRESETS = [
    "today",
    "week",
    "month",
    "3months",
    "6months",
    "year",
    "custom",
    "all",
]


def get_timezone():
    tz_name = current_app.config.get("TIMEZONE", "Asia/Kolkata") if current_app else "Asia/Kolkata"
    return ZoneInfo(tz_name)


def today():
    """Application 'today' in the configured timezone (not the server's)."""
    return datetime.now(get_timezone()).date()


def parse_date(value):
    """Parse a YYYY-MM-DD string into a date, or return None."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value.strip(), DATE_FMT).date()
    except (ValueError, AttributeError):
        return None


def format_date_for_db(d):
    return d.strftime(DATE_FMT) if d else None


def format_date_for_display(value):
    d = parse_date(value) if not isinstance(value, date) else value
    return d.strftime(DISPLAY_FMT) if d else ""


def get_period_dates(period, start_date=None, end_date=None):
    """Return (from_date, to_date) as date objects for a named preset.

    period: one of VALID_PRESETS.
    start_date/end_date: required (as 'YYYY-MM-DD' strings or date objects)
    when period == 'custom'.
    Raises ValueError on an invalid custom range.
    """
    t = today()

    if period == "today":
        return t, t
    if period == "week":
        start = t - timedelta(days=t.weekday())
        return start, t
    if period == "month":
        return t.replace(day=1), t
    if period == "3months":
        return t - timedelta(days=90), t
    if period == "6months":
        return t - timedelta(days=180), t
    if period == "year":
        return t.replace(month=1, day=1), t
    if period == "all":
        return None, None
    if period == "custom":
        from_d = parse_date(start_date)
        to_d = parse_date(end_date)
        if not from_d or not to_d:
            raise ValueError("Both From Date and To Date are required for a custom range.")
        if from_d > to_d:
            raise ValueError("From Date must be on or before To Date.")
        return from_d, to_d

    raise ValueError(f"Unknown date period: {period}")


def is_overdue(due_date, status):
    """A task is overdue when due_date is in the past and it's not finished."""
    d = parse_date(due_date)
    if not d:
        return False
    if status in ("COMPLETED", "CANCELLED"):
        return False
    return d < today()
