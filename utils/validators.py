"""Server-side validation. Never trust client-side validation alone."""
import re

from models import TASK_PRIORITIES, TASK_STATUSES
from utils.date_utils import parse_date

TITLE_MAX = 255
LONG_TEXT_MAX = 20000
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _err(errors, field, message):
    errors[field] = message


def validate_task(data):
    """data: dict-like with keys task_date, task_time, title, description,
    priority, status, due_date, notes.
    Returns dict of field -> error message (empty dict means valid).
    """
    errors = {}

    title = (data.get("title") or "").strip()
    if not title:
        _err(errors, "title", "Title is required.")
    elif len(title) > TITLE_MAX:
        _err(errors, "title", f"Title must be {TITLE_MAX} characters or fewer.")

    task_date = (data.get("task_date") or "").strip()
    if not task_date:
        _err(errors, "task_date", "Date is required.")
    elif not parse_date(task_date):
        _err(errors, "task_date", "Date must be a valid date (YYYY-MM-DD).")

    task_time = (data.get("task_time") or "").strip()
    if task_time and not TIME_RE.match(task_time):
        _err(errors, "task_time", "Time must be in HH:MM format.")

    priority = (data.get("priority") or "").strip().upper()
    if priority not in TASK_PRIORITIES:
        _err(errors, "priority", "Select a valid priority.")

    status = (data.get("status") or "").strip().upper()
    if status not in TASK_STATUSES:
        _err(errors, "status", "Select a valid status.")

    due_date = (data.get("due_date") or "").strip()
    if due_date and not parse_date(due_date):
        _err(errors, "due_date", "Due date must be a valid date (YYYY-MM-DD).")

    description = data.get("description") or ""
    if len(description) > LONG_TEXT_MAX:
        _err(errors, "description", "Description is too long.")

    notes = data.get("notes") or ""
    if len(notes) > LONG_TEXT_MAX:
        _err(errors, "notes", "Notes are too long.")

    return errors


def validate_status_value(status):
    return (status or "").strip().upper() in TASK_STATUSES


def validate_meeting(data):
    errors = {}

    title = (data.get("title") or "").strip()
    if not title:
        _err(errors, "title", "Meeting title is required.")
    elif len(title) > TITLE_MAX:
        _err(errors, "title", f"Title must be {TITLE_MAX} characters or fewer.")

    meeting_date = (data.get("meeting_date") or "").strip()
    if not meeting_date:
        _err(errors, "meeting_date", "Date is required.")
    elif not parse_date(meeting_date):
        _err(errors, "meeting_date", "Date must be a valid date (YYYY-MM-DD).")

    meeting_time = (data.get("meeting_time") or "").strip()
    if meeting_time and not TIME_RE.match(meeting_time):
        _err(errors, "meeting_time", "Time must be in HH:MM format.")

    for field in ("my_points", "meeting_points", "decisions", "notes"):
        value = data.get(field) or ""
        if len(value) > LONG_TEXT_MAX:
            _err(errors, field, "This field is too long.")

    return errors


def validate_custom_range(from_date, to_date):
    errors = {}
    f = parse_date(from_date)
    t = parse_date(to_date)
    if not f:
        _err(errors, "from_date", "From Date is required and must be valid.")
    if not t:
        _err(errors, "to_date", "To Date is required and must be valid.")
    if f and t and f > t:
        _err(errors, "to_date", "From Date must be on or before To Date.")
    return errors
