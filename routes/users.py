from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import ROLES, User
from utils.decorators import admin_required, handle_errors
from utils.validators import validate_user_form

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("")
@login_required
@admin_required
def list_view():
    users = User.get_all()
    return render_template("users/list.html", users=users)


@users_bp.route("/create", methods=["GET", "POST"])
@login_required
@admin_required
@handle_errors("Unable to create user.")
def create():
    if request.method == "POST":
        errors = validate_user_form(request.form, require_username=True, require_password=True)
        username = (request.form.get("username") or "").strip()
        if not errors.get("username") and User.get_by_username(username):
            errors["username"] = "That username is already taken."

        if not errors:
            User.create(
                username=username,
                password=request.form.get("password"),
                full_name=(request.form.get("full_name") or "").strip(),
                email=(request.form.get("email") or "").strip(),
                role=(request.form.get("role") or "user").strip().lower(),
            )
            flash(f"User '{username}' created successfully.", "success")
            return redirect(url_for("users.list_view"))

        flash("Please correct the errors below.", "danger")
        return render_template("users/form.html", user=request.form, errors=errors, roles=ROLES, mode="create")

    return render_template("users/form.html", user={}, errors={}, roles=ROLES, mode="create")


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
@handle_errors("Unable to update user.")
def edit(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users.list_view"))

    is_self = user.id == current_user.id

    if request.method == "POST":
        errors = validate_user_form(request.form, require_username=False, require_password=False)

        if is_self:
            # An admin can never change their own role or deactivate
            # themselves, regardless of what the form posts (defense in
            # depth even if a disabled field were tampered with client-side).
            new_role = user.role
            new_active = True
        else:
            new_role = (request.form.get("role") or "user").strip().lower()
            new_active = request.form.get("is_active") == "on"
            if user.role == "admin" and (new_role != "admin" or not new_active) and User.count_active_admins() <= 1:
                errors["role"] = "At least one active admin must remain."

        if not errors:
            User.update_profile(
                user_id=user.id,
                full_name=(request.form.get("full_name") or "").strip(),
                email=(request.form.get("email") or "").strip(),
                role=new_role,
                is_active=new_active,
            )
            new_password = request.form.get("password") or ""
            if new_password:
                User.set_password(user.id, new_password)
            flash(f"User '{user.username}' updated successfully.", "success")
            return redirect(url_for("users.list_view"))

        flash("Please correct the errors below.", "danger")
        merged = {
            "username": user.username,
            "full_name": request.form.get("full_name", user.full_name),
            "email": request.form.get("email", user.email),
            "role": new_role,
            "is_active": new_active,
        }
        return render_template(
            "users/form.html", user=merged, errors=errors, roles=ROLES, mode="edit",
            user_id=user.id, is_self=is_self,
        )

    return render_template(
        "users/form.html",
        user={
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
        errors={}, roles=ROLES, mode="edit", user_id=user.id, is_self=is_self,
    )


@users_bp.route("/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
@handle_errors("Unable to update user.")
def toggle_active(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users.list_view"))

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("users.list_view"))

    new_active = not user.is_active
    if user.role == "admin" and not new_active and User.count_active_admins() <= 1:
        flash("At least one active admin must remain.", "danger")
        return redirect(url_for("users.list_view"))

    User.update_profile(user.id, user.full_name, user.email, user.role, new_active)
    flash(f"User '{user.username}' {'activated' if new_active else 'deactivated'}.", "success")
    return redirect(url_for("users.list_view"))
