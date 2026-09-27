"""Admins can VIEW every user's tasks and meetings (oversight), but editing,
deleting, and status-updating another user's record stays restricted to its
owner. Regular (non-admin) users never get the owner-scope filter at all.
"""
from datetime import date

from models import User


def _login(client, username, password="password123"):
    client.get("/logout")
    return client.post("/login", data={"username": username, "password": password})


def _make_admin_and_user(app):
    with app.app_context():
        User.create(username="oversight_admin", password="password123", role="admin")
        User.create(username="worker", password="password123", role="user")


def test_regular_user_has_no_owner_filter(app, client):
    _make_admin_and_user(app)
    _login(client, "worker")
    response = client.get("/tasks")
    assert b'name="owner"' not in response.data


def test_admin_sees_owner_filter_and_all_users_scope(app, client):
    _make_admin_and_user(app)
    _login(client, "worker")
    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Worker's task",
            "priority": "MEDIUM",
            "status": "TODO",
        },
    )

    _login(client, "oversight_admin")
    response = client.get("/tasks")
    assert b'name="owner"' in response.data
    # default scope for an admin is still "my tasks" -> worker's task hidden
    assert b"Worker&#39;s task" not in response.data

    response = client.get("/tasks?owner=all")
    assert b"Worker&#39;s task" in response.data
    assert b"<th>Owner</th>" in response.data


def test_admin_can_view_but_not_edit_another_users_task(app, client):
    _make_admin_and_user(app)
    _login(client, "worker")
    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Worker task detail",
            "priority": "LOW",
            "status": "TODO",
        },
    )
    from database import get_db

    with app.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Worker task detail",)
        ).fetchone()["id"]

    _login(client, "oversight_admin")

    # Admin CAN view it, read-only
    detail = client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200
    assert b"read-only" in detail.data
    assert b"worker" in detail.data.lower()
    assert f"/tasks/{task_id}/edit".encode() not in detail.data

    # Admin CANNOT edit it via the edit route (still owner-scoped)
    edit_resp = client.get(f"/tasks/{task_id}/edit", follow_redirects=True)
    assert b"Task not found" in edit_resp.data

    # Admin CANNOT delete it either
    client.post(f"/tasks/{task_id}/delete")
    with app.app_context():
        still_there = get_db().execute(
            "SELECT id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert still_there is not None


def test_admin_meetings_oversight(app, client):
    _make_admin_and_user(app)
    _login(client, "worker")
    client.post(
        "/meetings/create",
        data={"meeting_date": date.today().isoformat(), "title": "Worker meeting"},
    )

    _login(client, "oversight_admin")
    response = client.get("/meetings?owner=all")
    assert b"Worker meeting" in response.data
    assert b"<th>Owner</th>" in response.data


def test_reports_owner_scope_for_admin(app, client):
    _make_admin_and_user(app)
    _login(client, "worker")
    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Worker report task",
            "priority": "MEDIUM",
            "status": "TODO",
        },
    )

    _login(client, "oversight_admin")
    response = client.get("/reports?period=year&owner=all")
    assert b"Worker report task" in response.data
    assert b"All Users" in response.data
