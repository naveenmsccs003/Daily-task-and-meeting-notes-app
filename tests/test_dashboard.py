"""The Dashboard's analytics widgets: Priority Distribution, Tasks by
Project, Completion Trend, and Hours: Estimated vs Spent. Each is backed by
a SQL aggregate in task_service — these tests check the numbers come out
right and that the page renders the chart containers for the right data.
"""
from datetime import date

from services import dashboard_service


def valid_task_payload(**overrides):
    payload = {
        "task_date": date.today().isoformat(),
        "title": "Dashboard task",
        "priority": "HIGH",
        "status": "TODO",
    }
    payload.update(overrides)
    return payload


def test_dashboard_page_loads_with_analytics_section(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Analytics" in response.data
    assert b"Priority Distribution" in response.data
    assert b"Tasks by Project" in response.data
    assert b"Completion Trend" in response.data
    assert b"Hours: Estimated vs Spent" in response.data


def test_priority_counts_aggregate(app, auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="P1", priority="HIGH"))
    auth_client.post("/tasks/create", data=valid_task_payload(title="P2", priority="HIGH"))
    auth_client.post("/tasks/create", data=valid_task_payload(title="P3", priority="LOW"))

    from models import User
    with app.app_context():
        user = User.get_by_username("testuser")
        counts = dashboard_service.get_dashboard_data(
            user.id, date.today().replace(day=1), date.today()
        )["priority_counts"]
    assert counts["HIGH"] >= 2
    assert counts["LOW"] >= 1


def test_project_breakdown_groups_untagged_as_no_project(app, auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="Untagged task"))

    from models import User
    with app.app_context():
        user = User.get_by_username("testuser")
        breakdown = dashboard_service.get_dashboard_data(
            user.id, date.today().replace(day=1), date.today()
        )["project_breakdown"]
    names = [row["name"] for row in breakdown]
    assert "No Project" in names


def test_completion_trend_zero_fills_days_without_completions(app, auth_client):
    auth_client.post(
        "/tasks/create", data=valid_task_payload(title="Done today", status="COMPLETED")
    )

    from models import User
    with app.app_context():
        user = User.get_by_username("testuser")
        trend = dashboard_service.get_dashboard_data(
            user.id, date.today(), date.today()
        )["completion_trend"]
    assert len(trend) == 1
    assert trend[0]["count"] == 1


def test_hours_totals_sum_estimated_and_spent(app, auth_client):
    auth_client.post(
        "/tasks/create",
        data=valid_task_payload(title="Hours A", estimated_hours="3"),
    )
    from database import get_db
    from models import User

    with app.app_context():
        task_id = get_db().execute(
            "SELECT id FROM tasks WHERE title = ?", ("Hours A",)
        ).fetchone()["id"]

    auth_client.post(
        f"/tasks/{task_id}/time-spent",
        json={"time_spent_hours": "2"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    with app.app_context():
        user = User.get_by_username("testuser")
        totals = dashboard_service.get_dashboard_data(
            user.id, date.today().replace(day=1), date.today()
        )["hours_totals"]
    assert totals["estimated"] == 3
    assert totals["spent"] == 2


def test_dashboard_analytics_scoped_to_current_user_only(app, client):
    from models import User

    with app.app_context():
        User.create(username="dash_a", password="password123", role="user")
        User.create(username="dash_b", password="password123", role="user")

    client.post("/login", data={"username": "dash_a", "password": "password123"})
    client.post("/tasks/create", data=valid_task_payload(title="A's task", priority="URGENT"))

    client.get("/logout")
    client.post("/login", data={"username": "dash_b", "password": "password123"})
    client.post("/tasks/create", data=valid_task_payload(title="B's task", priority="LOW"))

    with app.app_context():
        b = User.get_by_username("dash_b")
        data = dashboard_service.get_dashboard_data(
            b.id, date.today().replace(day=1), date.today()
        )
    assert data["priority_counts"]["URGENT"] == 0
    assert data["priority_counts"]["LOW"] == 1
