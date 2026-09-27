from datetime import date


def valid_task_payload(**overrides):
    payload = {
        "task_date": date.today().isoformat(),
        "task_time": "09:00",
        "title": "Prepare quarterly report",
        "description": "Include revenue figures",
        "priority": "HIGH",
        "status": "TODO",
        "due_date": "",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def test_create_task_valid(auth_client):
    response = auth_client.post("/tasks/create", data=valid_task_payload(), follow_redirects=True)
    assert response.status_code == 200
    assert b"Task created successfully" in response.data
    assert b"Prepare quarterly report" in response.data


def test_create_task_without_title_fails_validation(auth_client):
    response = auth_client.post(
        "/tasks/create", data=valid_task_payload(title=""), follow_redirects=True
    )
    assert b"Title is required" in response.data


def test_create_task_invalid_date_fails_validation(auth_client):
    response = auth_client.post(
        "/tasks/create", data=valid_task_payload(task_date="not-a-date"), follow_redirects=True
    )
    assert b"valid date" in response.data


def _create_task(auth_client, **overrides):
    auth_client.post("/tasks/create", data=valid_task_payload(**overrides))
    response = auth_client.get("/tasks")
    return response


def test_task_list_shows_created_task(auth_client):
    _create_task(auth_client)
    response = auth_client.get("/tasks")
    assert b"Prepare quarterly report" in response.data


def test_update_task_status_via_ajax(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    from database import get_db
    from app import create_app  # noqa

    # fetch the task id from the list page HTML is brittle; query directly
    with auth_client.application.app_context():
        row = get_db().execute("SELECT id FROM tasks ORDER BY id DESC LIMIT 1").fetchone()
        task_id = row["id"]

    response = auth_client.post(
        f"/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["status"] == "COMPLETED"


def test_update_task_status_invalid_value(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute("SELECT id FROM tasks ORDER BY id DESC LIMIT 1").fetchone()
        task_id = row["id"]

    response = auth_client.post(
        f"/tasks/{task_id}/status",
        json={"status": "NOT_A_STATUS"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    data = response.get_json()
    assert data["success"] is False


def test_delete_task(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute("SELECT id FROM tasks ORDER BY id DESC LIMIT 1").fetchone()
        task_id = row["id"]

    response = auth_client.post(f"/tasks/{task_id}/delete", follow_redirects=True)
    assert b"Task deleted successfully" in response.data


def test_search_tasks(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="Client meeting prep"))
    auth_client.post("/tasks/create", data=valid_task_payload(title="Unrelated item"))

    response = auth_client.get("/tasks?search=client")
    assert b"Client meeting prep" in response.data
    assert b"Unrelated item" not in response.data


def test_filter_tasks_by_status(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="Todo item", status="TODO"))
    auth_client.post("/tasks/create", data=valid_task_payload(title="Done item", status="COMPLETED"))

    response = auth_client.get("/tasks?status=COMPLETED")
    assert b"Done item" in response.data
    assert b"Todo item" not in response.data


def test_task_detail_404_for_missing_task(auth_client):
    response = auth_client.get("/tasks/99999", follow_redirects=True)
    assert b"Task not found" in response.data
