from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services import email_service, project_service
from utils.date_utils import format_date_for_db, get_period_dates, today

email_bp = Blueprint("email", __name__, url_prefix="/email")

MANUAL_PERIODS = [
    ("today", "Today", "Today's Report"),
    ("week", "This Week", "This Week's Report"),
    ("month", "This Month", "This Month's Report"),
    ("3months", "Last 3 Months", "Last 3 Months Report"),
    ("6months", "Last 6 Months", "Last 6 Months Report"),
    ("year", "This Year", "This Year's Report"),
    ("custom", "Custom", "Report"),
]
PERIOD_TITLES = {p[0]: p[2] for p in MANUAL_PERIODS}


def _selected_sections(form, prefix=""):
    return [s for s in email_service.SECTIONS if form.get(f"{prefix}{s}")]


def _render_page(send_form=None, send_errors=None, schedules=None, schedule_errors=None):
    if send_form is None:
        send_form = {
            "period": request.args.get("period", "today"),
            "start_date": request.args.get("start_date", ""),
            "end_date": request.args.get("end_date", ""),
            "project_id": request.args.get("project_id", ""),
            "recipients": current_user.email or "",
            "status": True, "tasks": True, "meetings": True,
        }
    return render_template(
        "email/index.html",
        configured=email_service.is_configured(),
        sender=email_service.sender_address(),
        send_form=send_form,
        send_errors=send_errors or {},
        periods=MANUAL_PERIODS,
        all_projects=project_service.list_projects(include_archived=False),
        frequencies=email_service.FREQUENCIES,
        schedules=schedules or email_service.get_schedules(current_user.id),
        schedule_errors=schedule_errors or {},
        send_hour=current_app.config["EMAIL_SEND_HOUR"],
        log=email_service.recent_log(current_user.id),
    )


@email_bp.route("")
@login_required
def index():
    return _render_page()


@email_bp.route("/send", methods=["POST"])
@login_required
def send():
    form = request.form
    errors = {}
    period = form.get("period", "today")
    if period not in PERIOD_TITLES:
        period = "today"
    try:
        from_date, to_date = get_period_dates(period, form.get("start_date"), form.get("end_date"))
    except ValueError as exc:
        errors["period"] = str(exc)
    recipients, recipient_error = email_service.parse_recipients(form.get("recipients"))
    if recipient_error:
        errors["recipients"] = recipient_error
    sections = _selected_sections(form)
    if not sections:
        errors["sections"] = "Choose at least one: Task Status, Tasks, or Meetings."

    if errors:
        flash("Please correct the errors below.", "danger")
        return _render_page(send_form=form, send_errors=errors)

    project_id = form.get("project_id", "", type=int) or None
    try:
        email_service.send_report(
            current_user, recipients, from_date, to_date, PERIOD_TITLES[period], sections,
            project_id=project_id,
        )
    except email_service.EmailError as exc:
        flash(str(exc), "danger")
        return _render_page(send_form=form)
    flash(f"Report emailed to {', '.join(recipients)}.", "success")
    return redirect(url_for("email.index"))


def _schedule_from_form(form, freq):
    prefix = f"{freq}_"
    return {
        "frequency": freq,
        "recipients": (form.get(prefix + "recipients") or "").strip(),
        "include_status": 1 if form.get(prefix + "status") else 0,
        "include_tasks": 1 if form.get(prefix + "tasks") else 0,
        "include_meetings": 1 if form.get(prefix + "meetings") else 0,
        "is_active": 1 if form.get(prefix + "active") else 0,
    }


def _validate_schedule(form, freq, require=False):
    """Returns (recipients, sections, error). Only an enabled schedule (or a
    send-now request, require=True) has to be complete."""
    prefix = f"{freq}_"
    sections = _selected_sections(form, prefix)
    needed = require or form.get(prefix + "active")
    recipients, error = email_service.parse_recipients(form.get(prefix + "recipients"))
    if error and not needed and not (form.get(prefix + "recipients") or "").strip():
        return [], sections, None
    if error:
        return [], sections, error
    if needed and not sections:
        return recipients, sections, "Choose at least one: Status, Tasks, or Meetings."
    return recipients, sections, None


@email_bp.route("/schedules", methods=["POST"])
@login_required
def save_schedules():
    form = request.form
    errors = {}
    validated = {}
    for freq in email_service.FREQUENCY_KEYS:
        recipients, sections, error = _validate_schedule(form, freq)
        if error:
            errors[freq] = error
        validated[freq] = (recipients, sections)

    if errors:
        saved = email_service.get_schedules(current_user.id)
        schedules = {f: {**saved[f], **_schedule_from_form(form, f)} for f in email_service.FREQUENCY_KEYS}
        flash("Please correct the errors below.", "danger")
        return _render_page(schedules=schedules, schedule_errors=errors)

    for freq, (recipients, sections) in validated.items():
        email_service.save_schedule(
            current_user.id, freq, recipients, sections, bool(form.get(f"{freq}_active"))
        )
    flash("Automatic email settings saved.", "success")
    return redirect(url_for("email.index") + "#schedules")


@email_bp.route("/schedules/<freq>/send", methods=["POST"])
@login_required
def send_schedule_now(freq):
    """Send the current period for one frequency right away, using the
    values currently in that row of the form (saved or not)."""
    if freq not in email_service.FREQUENCY_KEYS:
        flash("Unknown email frequency.", "danger")
        return redirect(url_for("email.index"))

    recipients, sections, error = _validate_schedule(request.form, freq, require=True)
    if error:
        saved = email_service.get_schedules(current_user.id)
        schedules = {f: {**saved[f], **_schedule_from_form(request.form, f)} for f in email_service.FREQUENCY_KEYS}
        flash("Please correct the errors below.", "danger")
        return _render_page(schedules=schedules, schedule_errors={freq: error})

    from_date, to_date = email_service.period_containing(freq, today())
    title = f"{email_service.FREQUENCY_LABELS[freq]} Report"
    try:
        email_service.send_report(current_user, recipients, from_date, to_date, title, sections, kind=freq)
    except email_service.EmailError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"{title} for {format_date_for_db(from_date)} to {format_date_for_db(to_date)} emailed to {', '.join(recipients)}.", "success")
    return redirect(url_for("email.index") + "#schedules")
