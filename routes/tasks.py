from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import TASK_PRIORITIES, TASK_STATUSES
from services import task_service
from utils.date_utils import get_period_dates
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
        "from_date": from_date,
        "to_date": to_date,
    }, period


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

    tasks, total = task_service.list_tasks(
        current_user.id, filters, page=page, per_page=per_page, sort=sort, sort_dir=sort_dir
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
    )


@tasks_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        errors = validate_task(request.form)
        if not errors:
            task_service.create_task(current_user.id, request.form)
            flash("Task created successfully.", "success")
            return redirect(url_for("tasks.list_view"))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "tasks/form.html", task=request.form, errors=errors,
            priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="create",
        )

    return render_template(
        "tasks/form.html", task={}, errors={}, priorities=TASK_PRIORITIES,
        statuses=TASK_STATUSES, mode="create",
    )


@tasks_bp.route("/<int:task_id>")
@login_required
def detail(task_id):
    task = task_service.get_task(current_user.id, task_id)
    if not task:
        flash("Task not found.", "warning")
        return redirect(url_for("tasks.list_view"))
    return render_template("tasks/detail.html", task=task)


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = task_service.get_task(current_user.id, task_id)
    if not task:
        flash("Task not found.", "warning")
        return redirect(url_for("tasks.list_view"))

    if request.method == "POST":
        errors = validate_task(request.form)
        if not errors:
            task_service.update_task(current_user.id, task_id, request.form)
            flash("Task updated successfully.", "success")
            return redirect(url_for("tasks.detail", task_id=task_id))
        flash("Please correct the errors below.", "danger")
        return render_template(
            "tasks/form.html", task=request.form, errors=errors, task_id=task_id,
            priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="edit",
        )

    return render_template(
        "tasks/form.html", task=task, errors={}, task_id=task_id,
        priorities=TASK_PRIORITIES, statuses=TASK_STATUSES, mode="edit",
    )


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    deleted = task_service.delete_task(current_user.id, task_id)
    message = "Task deleted successfully." if deleted else "Unable to delete task."
    if wants_json():
        return json_success(message) if deleted else json_error(message, status=404)
    flash(message, "success" if deleted else "danger")
    return redirect(url_for("tasks.list_view"))


@tasks_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
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
