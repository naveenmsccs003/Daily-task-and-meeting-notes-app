from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import TASK_PRIORITIES, TASK_STATUSES, User
from services import project_service, task_service
from services.task_service import ALL_USERS
from utils.date_utils import get_period_dates
from utils.decorators import handle_errors
from utils.helpers import json_error, json_success, wants_json
from utils.validators import validate_status_value, validate_task

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def _filters_from_request():
    period = request.args.get("period", "all")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    from_date, to_date = get_period_dates(period, start, end) if period != "all" else (None, None)

    return {
        "search": request.args.get("search", ""),
        "status": request.args.get("status", ""),
        "priority": request.args.get("priority", ""),
        "project_id": request.args.get("project_id", "", type=int) or None,
        "from_date": from_date,
        "to_date": to_date,
    }, period


def _resolve_owner_scope():
    """Admins may view their own tasks, everyone's, or one other user's via
    an `owner` query param ('me', 'all', or a user id). Everyone else is
    always scoped to themselves.
    """
    if not current_user.is_admin:
        return current_user.id, "me"

    owner_param = request.args.get("owner", "me")
    if owner_param == "all":
        return ALL_USERS, "all"
    if owner_param.isdigit():
        return int(owner_param), owner_param
    return current_user.id, "me"


def _resolve_assignee(default_owner_id):
    """Admin-only: pick who a task belongs to from the form's
    assigned_user_id field. Falls back to default_owner_id when absent,
    invalid, or the requester isn't an admin — regular users can never
    assign a task to anyone but themselves.
    """
    if not current_user.is_admin:
        return default_owner_id, None

    raw = (request.form.get("assigned_user_id") or "").strip()
    if not raw:
        return default_owner_id, None

    target = User.get_by_id(raw) if raw.isdigit() else None
    if not target:
        return default_owner_id, "Select a valid user to assign this task to."
    return target.id, None


@tasks_bp.route("")
@login_required
def list_view():
    try:
        filters, period = _filters_from_request()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("tasks.list_view"))

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "date")
    sort_dir = request.args.get("dir", "desc")
    per_page = current_app.config["TASKS_PER_PAGE"]

    owner_id, owner_scope = _resolve_owner_scope()

    tasks, total = task_service.list_tasks(
        owner_id, filters, page=page, per_page=per_page, sort=sort, sort_dir=sort_dir
    )
    total_pages = max((total + per_page - 1) // per_page, 1)

    return render_template(
        "tasks/list.html",
        tasks=tasks,
        total=total,
        page=page,
        total_pages=total_pages,
        sort=sort,
        sort_dir=sort_dir,
        period=period,
        filters=request.args,
        priorities=TASK_PRIORITIES,
        statuses=TASK_STATUSES,
        owner_scope=owner_scope,
        show_owner_column=owner_id != current_user.id,
        all_users=User.get_all() if current_user.is_admin else None,
        all_projects=project_service.list_projects(include_archived=False),
    )


@tasks_bp.route("/create", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to create task.")
def create():
    all_projects = project_service.list_projects(include_archived=False)
    all_users = User.get_all() if current_user.is_admin else None

    if request.method == "POST":
        errors = validate_task(request.form)
        owner_id, assignee_error = _resolve_assignee(current_user.id)
        if assignee_error:
            errors["assigned_user_id"] = assignee_error

        if not errors:
            task_service.create_task(owner_id, request.form)
            flash("Task created successfully.", "success")
            return redirect(url_for("tasks.list_view"))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "tasks/form.html", task=request.form, errors=errors,
            priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="create",
            all_projects=all_projects, all_users=all_users,
            selected_assignee_id=request.form.get("assigned_user_id") or current_user.id,
        )

    return render_template(
        "tasks/form.html", task={}, errors={}, priorities=TASK_PRIORITIES,
        statuses=TASK_STATUSES, mode="create", all_projects=all_projects,
        all_users=all_users, selected_assignee_id=current_user.id,
    )


@tasks_bp.route("/<int:task_id>")
@login_required
def detail(task_id):
    task = task_service.get_task(current_user.id, task_id)
    read_only = False
    if not task and current_user.is_admin:
        task = task_service.get_task_any(task_id)
        read_only = True
    if not task:
        flash("Task not found.", "warning")
        return redirect(url_for("tasks.list_view"))
    return render_template("tasks/detail.html", task=task, read_only=read_only)


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to update task.")
def edit(task_id):
    task = task_service.get_task(current_user.id, task_id)
    if not task:
        flash("Task not found.", "warning")
        return redirect(url_for("tasks.list_view"))

    all_projects = project_service.list_projects(include_archived=False)
    all_users = User.get_all() if current_user.is_admin else None

    if request.method == "POST":
        errors = validate_task(request.form)
        new_owner_id, assignee_error = _resolve_assignee(current_user.id)
        if assignee_error:
            errors["assigned_user_id"] = assignee_error

        if not errors:
            task_service.update_task(
                current_user.id, task_id, request.form,
                new_owner_id=new_owner_id if new_owner_id != current_user.id else None,
            )
            flash("Task updated successfully.", "success")
            if new_owner_id != current_user.id:
                flash("Task reassigned — it now appears in that user's task list.", "info")
                return redirect(url_for("tasks.list_view"))
            return redirect(url_for("tasks.detail", task_id=task_id))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "tasks/form.html", task=request.form, errors=errors, task_id=task_id,
            priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="edit",
            all_projects=all_projects, all_users=all_users,
            selected_assignee_id=request.form.get("assigned_user_id") or task["user_id"],
        )

    return render_template(
        "tasks/form.html", task=task, errors={}, task_id=task_id,
        priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="edit",
        all_projects=all_projects, all_users=all_users,
        selected_assignee_id=task["user_id"],
    )


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
@handle_errors("Unable to delete task.")
def delete(task_id):
    deleted = task_service.delete_task(current_user.id, task_id)
    message = "Task deleted successfully." if deleted else "Unable to delete task."
    if wants_json():
        return json_success(message) if deleted else json_error(message, status=404)
    flash(message, "success" if deleted else "danger")
    return redirect(url_for("tasks.list_view"))


@tasks_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
@handle_errors("Unable to update task status.")
def update_status(task_id):
    if request.is_json:
        status = (request.get_json(silent=True) or {}).get("status")
    else:
        status = request.form.get("status")

    if not validate_status_value(status):
        message = "Invalid status value."
        if wants_json():
            return json_error(message)
        flash(message, "danger")
        return redirect(url_for("tasks.list_view"))

    updated = task_service.update_status(current_user.id, task_id, status.upper())
    message = "Task status updated." if updated else "Unable to update task."

    if wants_json():
        return json_success(message, status=status.upper()) if updated else json_error(message, status=404)

    flash(message, "success" if updated else "danger")
    return redirect(request.referrer or url_for("tasks.list_view"))
