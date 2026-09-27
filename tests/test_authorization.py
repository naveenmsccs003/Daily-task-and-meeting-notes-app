"""Verify that one user's tasks/meetings are never visible or editable by
another logged-in user. Every service query filters by user_id; these tests
prove that filter actually holds at the HTTP layer.
"""
from datetime import date

from models import User


def _login(client, username, password="password123"):
    client.get("/logout")
    return client.post("/login", data={"username": username, "password": password})


def test_task_isolation_between_users(app, client):
    with app.app_context():
        User.create(username="owner", password="password123", full_name="Owner")
        User.create(username="intruder", password="password123", full_name="Intruder")

    _login(client, "owner")
    client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Owner's private task",
            "priority": "MEDIUM",
            "status": "TODO",
        },
    )
    from database import get_db

    with app.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Owner's private task",)
        ).fetchone()["id"]

    _login(client, "intruder")

    # Intruder cannot view the task
    detail = client.get(f"/tasks/{task_id}", follow_redirects=True)
    assert b"Task not found" in detail.data

    # Intruder's own task list must not contain the owner's task
    listing = client.get("/tasks")
    assert b"Owner&#39;s private task" not in listing.data
    assert b"Owner's private task" not in listing.data

    # Intruder cannot edit it
    edit_resp = client.get(f"/tasks/{task_id}/edit", follow_redirects=True)
    assert b"Task not found" in edit_resp.data

    # Intruder cannot delete it (service layer scopes the DELETE by user_id)
    client.post(f"/tasks/{task_id}/delete")
    with app.app_context():
        still_there = get_db().execute(
            "SELECT id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert still_there is not None

    # Intruder cannot flip its status via the AJAX endpoint either
    status_resp = client.post(
        f"/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert status_resp.get_json()["success"] is False


def test_meeting_isolation_between_users(app, client):
    with app.app_context():
        User.create(username="owner2", password="password123", full_name="Owner2")
        User.create(username="intruder2", password="password123", full_name="Intruder2")

    _login(client, "owner2")
    client.post(
        "/meetings/create",
        data={
            "meeting_date": date.today().isoformat(),
            "title": "Owner2 confidential meeting",
        },
    )
    from database import get_db

    with app.app_context():
        meeting_id = get_db().execute(
            "SELECT id FROM meetings WHERE title = ?", ("Owner2 confidential meeting",)
        ).fetchone()["id"]

    _login(client, "intruder2")

    detail = client.get(f"/meetings/{meeting_id}", follow_redirects=True)
    assert b"Meeting not found" in detail.data

    listing = client.get("/meetings")
    assert b"confidential" not in listing.data.lower()

    client.post(f"/meetings/{meeting_id}/delete")
    with app.app_context():
        still_there = get_db().execute(
            "SELECT id FROM meetings WHERE id = ?", (meeting_id,)
        ).fetchone()
    assert still_there is not None
