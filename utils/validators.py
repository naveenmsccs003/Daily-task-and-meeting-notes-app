"""Server-side validation. Never trust client-side validation alone."""
import re

from models import ROLES, TASK_PRIORITIES, TASK_STATUSES
from utils.date_utils import parse_date

TITLE_MAX = 255
LONG_TEXT_MAX = 20000
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_TIME_SPENT_HOURS = 999


def _err(errors, field, message):
    errors[field] = message


def parse_hours(raw, label="Value"):
    """Parse an hours-type field. Returns (value_or_None, error_or_None).
    An empty string is valid and means "not set" (value=None, no error).
    `label` (e.g. "Time spent", "Estimated time") is used to phrase the
    error message for whichever field is calling this.
    """
    raw = (raw or "").strip()
    if not raw:
        return None, None
    try:
        value = float(raw)
    except ValueError:
        return None, f"{label} must be a number (e.g. 1.5)."
    if value < 0 or value > MAX_TIME_SPENT_HOURS:
        return None, f"{label} must be between 0 and {MAX_TIME_SPENT_HOURS}."
    return value, None


def validate_task(data, allow_time_spent=True):
    """data: dict-like with keys task_date, task_time, title, description,
    priority, status, due_date, notes.
    allow_time_spent=False skips validating time_spent_hours entirely — used
    on task creation, where that field isn't shown (nothing to log time
    against yet), so any stray value in the request should be ignored
    rather than surfaced as an error the user can't see or fix.
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

    if allow_time_spent:
        _, time_spent_error = parse_hours(data.get("time_spent_hours"), "Time spent")
        if time_spent_error:
            _err(errors, "time_spent_hours", time_spent_error)

    _, estimated_error = parse_hours(data.get("estimated_hours"), "Estimated time")
    if estimated_error:
        _err(errors, "estimated_hours", estimated_error)

    project_id = (data.get("project_id") or "").strip()
    if project_id and not project_id.isdigit():
        _err(errors, "project_id", "Select a valid project.")

    assigned_user_id = (data.get("assigned_user_id") or "").strip()
    if assigned_user_id and not assigned_user_id.isdigit():
        _err(errors, "assigned_user_id", "Select a valid user.")

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

    project_id = (data.get("project_id") or "").strip()
    if project_id and not project_id.isdigit():
        _err(errors, "project_id", "Select a valid project.")

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


def validate_user_form(data, require_username=True, require_password=True):
    """Shared validation for the admin-only create/edit user forms.

    require_username: False on edit, since the username field is read-only there.
    require_password: True on create; on edit a blank password means "keep current".
    """
    errors = {}

    if require_username:
        username = (data.get("username") or "").strip()
        if not username:
            _err(errors, "username", "Username is required.")
        elif not USERNAME_RE.match(username):
            _err(errors, "username", "Username must be 3-50 characters: letters, numbers, dot, dash, or underscore.")

    password = data.get("password") or ""
    if require_password and not password:
        _err(errors, "password", "Password is required.")
    elif password and len(password) < 8:
        _err(errors, "password", "Password must be at least 8 characters.")

    full_name = (data.get("full_name") or "").strip()
    if len(full_name) > TITLE_MAX:
        _err(errors, "full_name", f"Full name must be {TITLE_MAX} characters or fewer.")

    email = (data.get("email") or "").strip()
    if email and not EMAIL_RE.match(email):
        _err(errors, "email", "Enter a valid email address.")

    role = (data.get("role") or "").strip().lower()
    if role not in ROLES:
        _err(errors, "role", "Select a valid role.")

    return errors


def validate_project_form(data):
    errors = {}

    name = (data.get("name") or "").strip()
    if not name:
        _err(errors, "name", "Project name is required.")
    elif len(name) > TITLE_MAX:
        _err(errors, "name", f"Project name must be {TITLE_MAX} characters or fewer.")

    description = data.get("description") or ""
    if len(description) > LONG_TEXT_MAX:
        _err(errors, "description", "Description is too long.")

    color = (data.get("color") or "").strip()
    if color and not HEX_COLOR_RE.match(color):
        _err(errors, "color", "Color must be a hex value like #4f46e5.")

    return errors
