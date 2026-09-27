from tests.test_meetings import valid_meeting_payload
from tests.test_tasks import valid_task_payload


def _seed(auth_client):
    auth_client.post("/tasks/create", data=valid_task_payload())
    auth_client.post("/meetings/create", data=valid_meeting_payload())


def test_export_excel(auth_client):
    _seed(auth_client)
    response = auth_client.get("/reports/export/excel?period=year")
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # XLSX files are zip archives and start with the PK signature
    assert response.data[:2] == b"PK"


def test_export_csv(auth_client):
    _seed(auth_client)
    response = auth_client.get("/reports/export/csv?period=year")
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data[:2] == b"PK"


def test_export_pdf(auth_client):
    _seed(auth_client)
    response = auth_client.get("/reports/export/pdf?period=year")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data[:4] == b"%PDF"


def test_export_requires_login(client):
    response = client.get("/reports/export/excel?period=year", follow_redirects=True)
    assert b"Please log in" in response.data or response.request.path == "/login"
