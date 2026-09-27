from datetime import date


def valid_task_payload(**overrides):
    payload = {
        "task_date": date.today().isoformat(),
        "title": "Estimation task",
        "priority": "MEDIUM",
        "status": "TODO",
    }
    payload.update(overrides)
    return payload


def test_create_task_with_estimated_hours(auth_client):
    response = auth_client.post(
        "/tasks/create",
        data=valid_task_payload(estimated_hours="4"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute(
            "SELECT estimated_hours FROM tasks WHERE title = ?", ("Estimation task",)
        ).fetchone()
    assert row["estimated_hours"] == 4.0


def test_estimated_hours_shown_on_detail_page(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(estimated_hours="2.5"))
    from database import get_db

    with auth_client.application.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Estimation task",)
        ).fetchone()["id"]

    response = auth_client.get(f"/tasks/{task_id}")
    assert b"Estimated Time" in response.data
    assert b"2.5 hrs" in response.data


def test_invalid_estimated_hours_rejected(auth_client):
    response = auth_client.post(
        "/tasks/create",
        data=valid_task_payload(estimated_hours="not-a-number"),
        follow_redirects=True,
    )
    assert b"Estimated time must be a number" in response.data


def test_inline_time_spent_update_via_ajax(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    from database import get_db

    with auth_client.application.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Estimation task",)
        ).fetchone()["id"]

    response = auth_client.post(
        f"/tasks/{task_id}/time-spent",
        json={"time_spent_hours": "3.25"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["time_spent_hours"] == 3.25

    with auth_client.application.app_context():
        row = get_db().execute(
            "SELECT time_spent_hours FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert row["time_spent_hours"] == 3.25


def test_inline_time_spent_update_rejects_invalid_value(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    from database import get_db

    with auth_client.application.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Estimation task",)
        ).fetchone()["id"]

    response = auth_client.post(
        f"/tasks/{task_id}/time-spent",
        json={"time_spent_hours": "abc"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    data = response.get_json()
    assert data["success"] is False


def test_inline_time_spent_clears_value(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(time_spent_hours="5"))
    from database import get_db

    with auth_client.application.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Estimation task",)
        ).fetchone()["id"]

    response = auth_client.post(
        f"/tasks/{task_id}/time-spent",
        json={"time_spent_hours": ""},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.get_json()["success"] is True

    with auth_client.application.app_context():
        row = get_db().execute(
            "SELECT time_spent_hours FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert row["time_spent_hours"] is None


def test_cannot_update_time_spent_on_others_task(app, client):
    from models import User

    with app.app_context():
        User.create(username="est_owner", password="password123", role="user")
        User.create(username="est_intruder", password="password123", role="user")

    client.post("/login", data={"username": "est_owner", "password": "password123"})
    client.post("/tasks/create", data=valid_task_payload(title="Owner task"))
    from database import get_db

    with app.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Owner task",)
        ).fetchone()["id"]

    client.get("/logout")
    client.post("/login", data={"username": "est_intruder", "password": "password123"})
    response = client.post(
        f"/tasks/{task_id}/time-spent",
        json={"time_spent_hours": "10"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.get_json()["success"] is False

    with app.app_context():
        row = get_db().execute(
            "SELECT time_spent_hours FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    assert row["time_spent_hours"] is None


def test_reports_show_estimated_hours_total(auth_client):
    auth_client.post(
        "/tasks/create",
        data=valid_task_payload(estimated_hours="6", status="COMPLETED"),
    )
    response = auth_client.get("/reports?period=today")
    assert b"Hours Estimated" in response.data
