from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services import project_service
from utils.decorators import handle_errors
from utils.helpers import json_error, json_success, wants_json
from utils.validators import validate_project_form

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


@projects_bp.route("")
@login_required
def list_view():
    projects = project_service.list_projects(include_archived=True)
    counts = {
        p["id"]: {
            "tasks": project_service.task_count(p["id"]),
            "meetings": project_service.meeting_count(p["id"]),
        }
        for p in projects
    }
    return render_template("projects/list.html", projects=projects, counts=counts)


@projects_bp.route("/create", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to create project.")
def create():
    if request.method == "POST":
        errors = validate_project_form(request.form)
        name = (request.form.get("name") or "").strip()
        if not errors.get("name") and project_service.get_by_name(name):
            errors["name"] = "A project with that name already exists."

        if not errors:
            project_service.create_project(
                name=name,
                description=(request.form.get("description") or "").strip(),
                color=(request.form.get("color") or "#4f46e5").strip(),
                created_by=current_user.id,
            )
            flash(f"Project '{name}' created successfully.", "success")
            return redirect(url_for("projects.list_view"))

        flash("Please correct the errors below.", "danger")
        return render_template("projects/form.html", project=request.form, errors=errors, mode="create")

    return render_template("projects/form.html", project={"color": "#4f46e5"}, errors={}, mode="create")


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
@handle_errors("Unable to update project.")
def edit(project_id):
    project = project_service.get_project(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("projects.list_view"))

    if request.method == "POST":
        errors = validate_project_form(request.form)
        name = (request.form.get("name") or "").strip()
        existing = project_service.get_by_name(name)
        if not errors.get("name") and existing and existing["id"] != project_id:
            errors["name"] = "A project with that name already exists."

        if not errors:
            project_service.update_project(
                project_id,
                name=name,
                description=(request.form.get("description") or "").strip(),
                color=(request.form.get("color") or "#4f46e5").strip(),
            )
            flash(f"Project '{name}' updated successfully.", "success")
            return redirect(url_for("projects.list_view"))

        flash("Please correct the errors below.", "danger")
        return render_template(
            "projects/form.html", project=request.form, errors=errors, mode="edit", project_id=project_id
        )

    return render_template("projects/form.html", project=project, errors={}, mode="edit", project_id=project_id)


@projects_bp.route("/<int:project_id>/toggle-active", methods=["POST"])
@login_required
@handle_errors("Unable to update project.")
def toggle_active(project_id):
    project = project_service.get_project(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("projects.list_view"))

    new_active = not project["is_active"]
    project_service.set_active(project_id, new_active)
    message = f"Project '{project['name']}' {'reactivated' if new_active else 'archived'}."
    if wants_json():
        return json_success(message)
    flash(message, "success")
    return redirect(url_for("projects.list_view"))
