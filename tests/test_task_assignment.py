"""Admins can assign a task to another user at creation or via edit; the
task then belongs entirely to the assignee (moves into their own task
list). Regular users never get this option and can only create tasks for
themselves.
"""
from datetime import date

from models import User


def _login(client, username, password="password123"):
    client.get("/logout")
    return client.post("/login", data={"username": username, "password": password})


def _make_admin_and_user(app):
    with app.app_context():
        User.create(username="assign_admin", password="password123", role="admin")
        User.create(username="assign_worker", password="password123", role="user")


def test_regular_user_has_no_assign_to_field(auth_client):
    response = auth_client.get("/tasks/create")
    assert b"Assign To" not in response.data
    assert b'name="assigned_user_id"' not in response.data


def test_admin_sees_assign_to_field(app, client):
    _make_admin_and_user(app)
    _login(client, "assign_admin")
    response = client.get("/tasks/create")
    assert b"Assign To" in response.data
    assert b'name="assigned_user_id"' in response.data


def test_admin_creates_task_assigned_to_another_user(app, client):
    _make_admin_and_user(app)
    _login(client, "assign_admin")

    with app.app_context():
        worker = User.get_by_username("assign_worker")

    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Handed-off task",
            "priority": "MEDIUM",
            "status": "TODO",
            "assigned_user_id": str(worker.id),
        },
    )

    # Not in admin's own "My Tasks" list
    admin_tasks = client.get("/tasks")
    assert b"Handed-off task" not in admin_tasks.data

    # Shows up for the assignee
    _login(client, "assign_worker")
    worker_tasks = client.get("/tasks")
    assert b"Handed-off task" in worker_tasks.data


def test_regular_user_cannot_assign_task_via_manual_field(app, client):
    _make_admin_and_user(app)
    with app.app_context():
        admin = User.get_by_username("assign_admin")

    _login(client, "assign_worker")
    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Should stay mine",
            "priority": "MEDIUM",
            "status": "TODO",
            "assigned_user_id": str(admin.id),  # attempted privilege escalation
        },
    )

    # Task belongs to the worker, not the admin, despite the posted field
    from database import get_db

    with app.app_context():
        row = get_db().execute(
            "SELECT user_id FROM tasks WHERE title = ?", ("Should stay mine",)
        ).fetchone()
        worker = User.get_by_username("assign_worker")
    assert row["user_id"] == worker.id


def test_admin_reassigns_own_task_via_edit(app, client):
    _make_admin_and_user(app)
    _login(client, "assign_admin")

    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Reassign me",
            "priority": "MEDIUM",
            "status": "TODO",
        },
    )
    from database import get_db

    with app.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Reassign me",)
        ).fetchone()["id"]
        worker = User.get_by_username("assign_worker")

    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "task_date": date.today().isoformat(),
            "title": "Reassign me",
            "priority": "MEDIUM",
            "status": "TODO",
            "assigned_user_id": str(worker.id),
        },
        follow_redirects=True,
    )
    assert b"reassigned" in response.data

    with app.app_context():
        row = get_db().execute(
            "SELECT user_id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert row["user_id"] == worker.id
