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


def test_reports_build_report_includes_chart_data(app):
    from services import report_service, task_service
    from utils.date_utils import today

    with app.app_context():
        from database import get_db
        db = get_db()
        user_id = db.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]

        report = report_service.build_report(user_id, today(), today())

        assert set(report["priority_counts"].keys()) == {"LOW", "MEDIUM", "HIGH", "URGENT"}
        assert isinstance(report["project_breakdown"], list)
        assert isinstance(report["completion_trend"], list)
        assert set(report["hours_totals"].keys()) == {"estimated", "spent"}


def test_reports_chart_data_respects_project_filter(auth_client, app):
    from services import project_service, report_service
    from utils.date_utils import today

    with app.app_context():
        from database import get_db
        db = get_db()
        user_id = db.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        project_id = project_service.create_project("Filter Test Project", "", "#111111", user_id)

    auth_client.post("/tasks/create", data=valid_task_payload(title="Filtered Task", project_id=project_id))

    with app.app_context():
        report = report_service.build_report(user_id, today(), today(), project_id=project_id)
        assert report["summary"]["total_tasks"] == 1
        assert sum(report["priority_counts"].values()) == 1
