from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import User
from services import meeting_service, project_service
from services.meeting_service import ALL_USERS
from utils.date_utils import get_period_dates
from utils.decorators import handle_errors
from utils.helpers import json_error, json_success, wants_json
from utils.validators import validate_meeting

meetings_bp = Blueprint("meetings", __name__, url_prefix="/meetings")


def _filters_from_request():
    period = request.args.get("period", "all")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    from_date, to_date = get_period_dates(period, start, end) if period != "all" else (None, None)

    return {
        "search": request.args.get("search", ""),
        "project_id": request.args.get("project_id", "", type=int) or None,
        "from_date": from_date,
        "to_date": to_date,
    }, period


def _resolve_owner_scope():
    if not current_user.is_admin:
        return current_user.id, "me"

    owner_param = request.args.get("owner", "me")
    if owner_param == "all":
        return ALL_USERS, "all"
    if owner_param.isdigit():
        return int(owner_param), owner_param
    return current_user.id, "me"


@meetings_bp.route("")
@login_required
def list_view():
    try:
        filters, period = _filters_from_request()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("meetings.list_view"))

    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["MEETINGS_PER_PAGE"]

    owner_id, owner_scope = _resolve_owner_scope()

    meetings, total = meeting_service.list_meetings(
        owner_id, filters, page=page, per_page=per_page
    )
    total_pages = max((total + per_page - 1) // per_page, 1)

    return render_template(
        "meetings/list.html",
        meetings=meetings,
        total=total,
        page=page,
        total_pages=total_pages,
        period=period,
        filters=request.args,
        owner_scope=owner_scope,
        show_owner_column=owner_id != current_user.id,
        all_users=User.get_all() if current_user.is_admin else None,
        all_projects=project_service.list_projects(include_archived=False),
    )


@meetings_bp.route("/create", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to create meeting.")
def create():
    all_projects = project_service.list_projects(include_archived=False)

    if request.method == "POST":
        errors = validate_meeting(request.form)
        if not errors:
            meeting_service.create_meeting(current_user.id, request.form)
            flash("Meeting created successfully.", "success")
            return redirect(url_for("meetings.list_view"))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "meetings/form.html", meeting=request.form, errors=errors, mode="create",
            all_projects=all_projects,
        )

    return render_template(
        "meetings/form.html", meeting={}, errors={}, mode="create", all_projects=all_projects
    )


@meetings_bp.route("/<int:meeting_id>")
@login_required
def detail(meeting_id):
    meeting = meeting_service.get_meeting(current_user.id, meeting_id)
    read_only = False
    if not meeting and current_user.is_admin:
        meeting = meeting_service.get_meeting_any(meeting_id)
        read_only = True
    if not meeting:
        flash("Meeting not found.", "warning")
        return redirect(url_for("meetings.list_view"))
    return render_template("meetings/detail.html", meeting=meeting, read_only=read_only)


@meetings_bp.route("/<int:meeting_id>/edit", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to update meeting.")
def edit(meeting_id):
    meeting = meeting_service.get_meeting(current_user.id, meeting_id)
    if not meeting:
        flash("Meeting not found.", "warning")
        return redirect(url_for("meetings.list_view"))

    all_projects = project_service.list_projects(include_archived=False)

    if request.method == "POST":
        errors = validate_meeting(request.form)
        if not errors:
            meeting_service.update_meeting(current_user.id, meeting_id, request.form)
            flash("Meeting updated successfully.", "success")
            return redirect(url_for("meetings.detail", meeting_id=meeting_id))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "meetings/form.html", meeting=request.form, errors=errors,
            meeting_id=meeting_id, mode="edit", all_projects=all_projects,
        )

    return render_template(
        "meetings/form.html", meeting=meeting, errors={}, meeting_id=meeting_id, mode="edit",
        all_projects=all_projects,
    )


@meetings_bp.route("/<int:meeting_id>/delete", methods=["POST"])
@login_required
@handle_errors("Unable to delete meeting.")
def delete(meeting_id):
    deleted = meeting_service.delete_meeting(current_user.id, meeting_id)
    message = "Meeting deleted successfully." if deleted else "Unable to delete meeting."
    if wants_json():
        return json_success(message) if deleted else json_error(message, status=404)
    flash(message, "success" if deleted else "danger")
    return redirect(url_for("meetings.list_view"))
