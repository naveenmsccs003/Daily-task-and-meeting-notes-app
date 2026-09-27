"""Report emails: builds a point-by-point summary of tasks, meetings, and task
status for a date range, sends it over SMTP, and runs the automatic
daily/weekly/monthly/6-monthly/yearly schedules.

Sending uses only the standard library (smtplib), configured by the MAIL_*
settings in config.py. Every send attempt is recorded in email_log.
"""
import re
import smtplib
import ssl
import threading
import time
from datetime import datetime, timedelta
from datetime import time as dtime
from email.message import EmailMessage
from email.utils import formataddr

from flask import current_app, render_template

from database import get_db
from models import User
from services import report_service
from utils.date_utils import format_date_for_display, get_timezone

# (key, label, when-it-is-sent description)
FREQUENCIES = [
    ("daily", "Daily", "Every day — covers that day"),
    ("weekly", "Weekly", "Every Sunday — covers Monday to Sunday"),
    ("monthly", "Monthly", "Last day of each month — covers the month"),
    ("6months", "Every 6 Months", "30 Jun and 31 Dec — covers each half-year"),
    ("yearly", "Yearly", "31 Dec — covers the whole year"),
]
FREQUENCY_KEYS = [f[0] for f in FREQUENCIES]
FREQUENCY_LABELS = {f[0]: f[1] for f in FREQUENCIES}

SECTIONS = ("status", "tasks", "meetings")

EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")

# After a failed scheduled send, wait this long before retrying the same period.
RETRY_AFTER = timedelta(hours=1)


class EmailError(Exception):
    """A send failed or email is not configured; the message is user-safe."""


# ---------------------------------------------------------------- recipients

def parse_recipients(raw):
    """Split a comma/semicolon/space separated list. Returns (emails, error)."""
    parts = [p.strip() for p in re.split(r"[,;\s]+", raw or "") if p.strip()]
    if not parts:
        return [], "Enter at least one email address."
    bad = [p for p in parts if not EMAIL_RE.match(p)]
    if bad:
        return [], f"Invalid email address: {', '.join(bad)}"
    # De-duplicate, keeping order.
    seen = []
    for p in parts:
        if p.lower() not in [s.lower() for s in seen]:
            seen.append(p)
    return seen, None


# ------------------------------------------------------------------- content

def to_points(text):
    """Turn a free-text field into a list of bullet points, one per line,
    stripping any bullet characters the user already typed."""
    points = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•·]+|\d+[.)])\s*", "", line).strip()
        if line:
            points.append(line)
    return points


def status_label(value):
    return (value or "").replace("_", " ").title()


def build_report_email(user, from_date, to_date, title, sections, project_id=None):
    """Return (subject, text_body, html_body) for the user's own data."""
    report = report_service.build_report(user.id, from_date, to_date, project_id=project_id)
    sections = set(sections)
    context = {
        "report": report,
        "title": title,
        "user_name": user.full_name or user.username,
        "show_status": "status" in sections,
        "show_tasks": "tasks" in sections,
        "show_meetings": "meetings" in sections,
        "points": to_points,
        "status_label": status_label,
        "display_date": format_date_for_display,
        "generated_at": datetime.now(get_timezone()).strftime("%d %b %Y %H:%M"),
    }
    subject = f"{title}: {report['range_label']} - Task & Meeting Tracker"
    text_body = render_template("email/report.txt", **context)
    html_body = render_template("email/report.html", **context)
    return subject, text_body, html_body


# ------------------------------------------------------------------- sending

def is_configured():
    return bool(current_app.config.get("MAIL_SERVER"))


def sender_address():
    cfg = current_app.config
    return cfg.get("MAIL_DEFAULT_SENDER") or cfg.get("MAIL_USERNAME") or ""


def send_email(recipients, subject, text_body, html_body):
    cfg = current_app.config
    if not is_configured():
        raise EmailError("Email is not set up yet. Add the MAIL_* settings to your .env file and restart the app.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Task & Meeting Tracker", sender_address()))
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    host, port = cfg["MAIL_SERVER"], cfg["MAIL_PORT"]
    try:
        if cfg.get("MAIL_USE_SSL"):
            smtp = smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(host, port, timeout=30)
        with smtp:
            if cfg.get("MAIL_USE_TLS") and not cfg.get("MAIL_USE_SSL"):
                smtp.starttls(context=ssl.create_default_context())
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        current_app.logger.warning("SMTP login failed: %s", exc)
        raise EmailError("The mail server rejected the username/password (for Gmail, use an App Password).") from exc
    except (smtplib.SMTPException, OSError) as exc:
        current_app.logger.warning("Email send failed: %s", exc)
        raise EmailError(f"Could not send email: {exc}") from exc


def _log(user_id, kind, subject, recipients, error=None):
    db = get_db()
    db.execute(
        """INSERT INTO email_log (user_id, kind, subject, recipients, success, error, sent_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, kind, subject, ", ".join(recipients), 0 if error else 1, error,
         _now().strftime("%Y-%m-%d %H:%M")),
    )
    db.commit()


def send_report(user, recipients, from_date, to_date, title, sections, kind="manual", project_id=None):
    """Build, send, and log one report email. Raises EmailError on failure."""
    subject, text_body, html_body = build_report_email(
        user, from_date, to_date, title, sections, project_id=project_id
    )
    try:
        send_email(recipients, subject, text_body, html_body)
    except EmailError as exc:
        _log(user.id, kind, subject, recipients, error=str(exc))
        raise
    _log(user.id, kind, subject, recipients)
    return subject


def recent_log(user_id, limit=20):
    return get_db().execute(
        "SELECT * FROM email_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


# ---------------------------------------------------------------- schedules

def period_containing(frequency, d):
    """Calendar period (start, end) of the given frequency that contains date d."""
    if frequency == "daily":
        return d, d
    if frequency == "weekly":
        start = d - timedelta(days=d.weekday())
        return start, start + timedelta(days=6)
    if frequency == "monthly":
        start = d.replace(day=1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        return start, next_month - timedelta(days=1)
    if frequency == "6months":
        if d.month <= 6:
            return d.replace(month=1, day=1), d.replace(month=6, day=30)
        return d.replace(month=7, day=1), d.replace(month=12, day=31)
    if frequency == "yearly":
        return d.replace(month=1, day=1), d.replace(month=12, day=31)
    raise ValueError(f"Unknown frequency: {frequency}")


def due_period(frequency, now):
    """The most recent period whose send time (its last day at
    EMAIL_SEND_HOUR) has already passed."""
    start, end = period_containing(frequency, now.date())
    due_at = datetime.combine(end, dtime(hour=current_app.config["EMAIL_SEND_HOUR"]), tzinfo=now.tzinfo)
    if now >= due_at:
        return start, end
    return period_containing(frequency, start - timedelta(days=1))


def period_key(frequency, start):
    return f"{frequency}:{start.isoformat()}"


def _now():
    return datetime.now(get_timezone())


def get_schedules(user_id):
    """Dict keyed by frequency; frequencies never saved get default values."""
    rows = get_db().execute(
        "SELECT * FROM email_schedules WHERE user_id = ?", (user_id,)
    ).fetchall()
    by_freq = {row["frequency"]: dict(row) for row in rows}
    user = User.get_by_id(user_id)
    for freq in FREQUENCY_KEYS:
        by_freq.setdefault(freq, {
            "frequency": freq,
            "recipients": (user.email if user else "") or "",
            "include_status": 1,
            "include_tasks": 1,
            "include_meetings": 1,
            "is_active": 0,
            "last_sent_at": None,
        })
    return by_freq


def save_schedule(user_id, frequency, recipients, sections, is_active):
    db = get_db()
    existing = db.execute(
        "SELECT is_active FROM email_schedules WHERE user_id = ? AND frequency = ?",
        (user_id, frequency),
    ).fetchone()
    was_active = bool(existing and existing["is_active"])
    values = (
        ", ".join(recipients),
        1 if "status" in sections else 0,
        1 if "tasks" in sections else 0,
        1 if "meetings" in sections else 0,
        1 if is_active else 0,
    )
    if existing:
        db.execute(
            """UPDATE email_schedules SET recipients = ?, include_status = ?, include_tasks = ?,
               include_meetings = ?, is_active = ?, updated_at = datetime('now')
               WHERE user_id = ? AND frequency = ?""",
            (*values, user_id, frequency),
        )
    else:
        db.execute(
            """INSERT INTO email_schedules (recipients, include_status, include_tasks,
               include_meetings, is_active, user_id, frequency) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (*values, user_id, frequency),
        )
    if is_active and not was_active:
        # Switching a schedule on should not immediately fire for a period
        # that already ended; the first email is the next one due.
        start, _end = due_period(frequency, _now())
        db.execute(
            "UPDATE email_schedules SET last_sent_key = ? WHERE user_id = ? AND frequency = ?",
            (period_key(frequency, start), user_id, frequency),
        )
    db.commit()


def schedule_sections(schedule):
    return [s for s in SECTIONS if schedule[f"include_{s}"]]


def run_due_schedules(now=None):
    """Send every active schedule whose latest period has not been sent yet.
    Returns the number of emails sent. Safe to call repeatedly."""
    if not is_configured():
        return 0
    now = now or _now()
    db = get_db()
    rows = db.execute(
        """SELECT email_schedules.* FROM email_schedules
           JOIN users ON users.id = email_schedules.user_id
           WHERE email_schedules.is_active = 1 AND users.is_active = 1"""
    ).fetchall()
    sent = 0
    for row in rows:
        start, end = due_period(row["frequency"], now)
        key = period_key(row["frequency"], start)
        if row["last_sent_key"] == key:
            continue
        if row["last_attempt_at"]:
            last_attempt = datetime.fromisoformat(row["last_attempt_at"])
            if now - last_attempt < RETRY_AFTER:
                continue

        recipients, error = parse_recipients(row["recipients"])
        user = User.get_by_id(row["user_id"])
        if error or not user:
            continue
        db.execute(
            "UPDATE email_schedules SET last_attempt_at = ? WHERE id = ?",
            (now.isoformat(), row["id"]),
        )
        db.commit()
        title = f"{FREQUENCY_LABELS[row['frequency']]} Report"
        try:
            send_report(user, recipients, start, end, title, schedule_sections(row), kind=row["frequency"])
        except EmailError:
            continue
        db.execute(
            """UPDATE email_schedules SET last_sent_key = ?, last_sent_at = ?, last_attempt_at = NULL
               WHERE id = ?""",
            (key, now.strftime("%Y-%m-%d %H:%M"), row["id"]),
        )
        db.commit()
        sent += 1
    return sent


def start_scheduler(app):
    """Background thread that checks for due schedules every few minutes
    while the app is running."""
    interval = app.config["EMAIL_CHECK_INTERVAL_SECONDS"]

    def loop():
        while True:
            try:
                with app.app_context():
                    run_due_schedules()
            except Exception:
                app.logger.exception("Scheduled email check failed")
            time.sleep(interval)

    thread = threading.Thread(target=loop, name="email-scheduler", daemon=True)
    thread.start()
    return thread
