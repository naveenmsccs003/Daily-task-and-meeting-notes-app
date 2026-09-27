from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import User
from services import export_service, project_service, report_service
from services.task_service import ALL_USERS
from utils.date_utils import format_date_for_db, get_period_dates
from utils.helpers import safe_export_filename

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _resolve_range():
    period = request.args.get("period", "month")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    from_date, to_date = get_period_dates(period, start, end)
    return period, from_date, to_date


def _resolve_owner_scope():
    if not current_user.is_admin:
        return current_user.id, "me", "My Data"

    owner_param = request.args.get("owner", "me")
    if owner_param == "all":
        return ALL_USERS, "all", "All Users"
    if owner_param.isdigit():
        target = User.get_by_id(int(owner_param))
        if target:
            return target.id, owner_param, (target.full_name or target.username)
    return current_user.id, "me", "My Data"


@reports_bp.route("")
@login_required
def index():
    try:
        period, from_date, to_date = _resolve_range()
    except ValueError as exc:
        flash(str(exc), "danger")
        period, from_date, to_date = "month", *get_period_dates("month")

    owner_id, owner_scope, owner_label = _resolve_owner_scope()
    project_id = request.args.get("project_id", "", type=int) or None
    report = report_service.build_report(owner_id, from_date, to_date, project_id=project_id)

    return render_template(
        "reports/index.html",
        report=report,
        period=period,
        from_date=format_date_for_db(from_date) if from_date else "",
        to_date=format_date_for_db(to_date) if to_date else "",
        owner_scope=owner_scope,
        owner_label=owner_label,
        all_users=User.get_all() if current_user.is_admin else None,
        all_projects=project_service.list_projects(include_archived=False),
        project_id=project_id,
    )


def _report_for_export():
    period, from_date, to_date = _resolve_range()
    owner_id, _owner_scope, _owner_label = _resolve_owner_scope()
    project_id = request.args.get("project_id", "", type=int) or None
    return report_service.build_report(owner_id, from_date, to_date, project_id=project_id)


@reports_bp.route("/export/excel")
@login_required
def export_excel():
    try:
        report = _report_for_export()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.index"))

    buffer = export_service.generate_excel(report)
    filename = safe_export_filename("task_meeting_report", "xlsx")
    return Response(
        buffer.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    try:
        report = _report_for_export()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.index"))

    buffer = export_service.generate_csv_zip(report)
    filename = safe_export_filename("task_meeting_report", "zip")
    return Response(
        buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/pdf")
@login_required
def export_pdf():
    try:
        report = _report_for_export()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.index"))

    buffer = export_service.generate_pdf(report)
    filename = safe_export_filename("task_meeting_report", "pdf")
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
