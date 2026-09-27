from datetime import date


def test_create_project(auth_client):
    response = auth_client.post(
        "/projects/create",
        data={"name": "Project Alpha", "description": "Q4 launch", "color": "#ff0000"},
        follow_redirects=True,
    )
    assert b"created successfully" in response.data
    assert b"Project Alpha" in response.data


def test_create_project_without_name_fails(auth_client):
    response = auth_client.post(
        "/projects/create", data={"name": "", "color": "#ff0000"}, follow_redirects=True
    )
    assert b"Project name is required" in response.data


def test_create_duplicate_project_name_fails(auth_client):
    auth_client.post("/projects/create", data={"name": "Dup Project", "color": "#ff0000"})
    response = auth_client.post(
        "/projects/create", data={"name": "Dup Project", "color": "#00ff00"}, follow_redirects=True
    )
    assert b"already exists" in response.data


def test_archive_and_reactivate_project(auth_client):
    auth_client.post("/projects/create", data={"name": "Archive Me", "color": "#4f46e5"})
    from database import get_db

    with auth_client.application.app_context():
        project_id = get_db().execute(
            "SELECT id FROM projects WHERE name = ?", ("Archive Me",)
        ).fetchone()["id"]

    response = auth_client.post(f"/projects/{project_id}/toggle-active", follow_redirects=True)
    assert b"archived" in response.data

    response = auth_client.post(f"/projects/{project_id}/toggle-active", follow_redirects=True)
    assert b"reactivated" in response.data


def test_task_can_be_tagged_with_project_and_filtered(auth_client):
    auth_client.post("/projects/create", data={"name": "Tagging Project", "color": "#4f46e5"})
    from database import get_db

    with auth_client.application.app_context():
        project_id = get_db().execute(
            "SELECT id FROM projects WHERE name = ?", ("Tagging Project",)
        ).fetchone()["id"]

    auth_client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Tagged task",
            "priority": "MEDIUM",
            "status": "TODO",
            "project_id": str(project_id),
        },
    )
    auth_client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Untagged task",
            "priority": "MEDIUM",
            "status": "TODO",
        },
    )

    response = auth_client.get(f"/tasks?project_id={project_id}")
    assert b"Tagged task" in response.data
    assert b"Untagged task" not in response.data

    detail = auth_client.get("/tasks")
    assert b"Tagging Project" in detail.data


def test_meeting_can_be_tagged_with_project(auth_client):
    auth_client.post("/projects/create", data={"name": "Meeting Project", "color": "#4f46e5"})
    from database import get_db

    with auth_client.application.app_context():
        project_id = get_db().execute(
            "SELECT id FROM projects WHERE name = ?", ("Meeting Project",)
        ).fetchone()["id"]

    auth_client.post(
        "/meetings/create",
        data={
            "meeting_date": date.today().isoformat(),
            "title": "Project sync",
            "project_id": str(project_id),
        },
    )

    response = auth_client.get(f"/meetings?project_id={project_id}")
    assert b"Project sync" in response.data


def test_task_time_spent_saved_and_validated(auth_client):
    response = auth_client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Timed task",
            "priority": "MEDIUM",
            "status": "TODO",
            "time_spent_hours": "not-a-number",
        },
        follow_redirects=True,
    )
    assert b"must be a number" in response.data

    auth_client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Timed task 2",
            "priority": "MEDIUM",
            "status": "TODO",
            "time_spent_hours": "2.5",
        },
    )
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute(
            "SELECT time_spent_hours FROM tasks WHERE title = ?", ("Timed task 2",)
        ).fetchone()
    assert row["time_spent_hours"] == 2.5


def test_reports_total_hours_logged(auth_client):
    auth_client.post(
        "/tasks/create",
        data={
            "task_date": date.today().isoformat(),
            "title": "Hours task",
            "priority": "MEDIUM",
            "status": "COMPLETED",
            "time_spent_hours": "3",
        },
    )
    response = auth_client.get("/reports?period=today")
    assert b"Hours Logged" in response.data
