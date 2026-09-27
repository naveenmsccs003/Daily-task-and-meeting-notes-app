from datetime import date

from tests.test_tasks import valid_task_payload


def test_reports_page_loads(auth_client):
    response = auth_client.get("/reports")
    assert response.status_code == 200
    assert b"Reports" in response.data


def test_reports_today_filter_shows_only_todays_task(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="Today task"))
    response = auth_client.get("/reports?period=today")
    assert b"Today task" in response.data


def test_reports_custom_range_requires_both_dates(auth_client):
    response = auth_client.get("/reports?period=custom&start_date=&end_date=", follow_redirects=True)
    assert b"required" in response.data.lower()


def test_reports_custom_range_invalid_order(auth_client):
    response = auth_client.get(
        "/reports?period=custom&start_date=2026-01-10&end_date=2026-01-01",
        follow_redirects=True,
    )
    assert b"on or before" in response.data.lower()


def test_reports_summary_counts(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload(title="Task A", status="COMPLETED"))
    auth_client.post("/tasks/create", data=valid_task_payload(title="Task B", status="TODO"))
    response = auth_client.get(f"/reports?period=today")
    assert response.status_code == 200
