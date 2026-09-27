from datetime import date


def valid_meeting_payload(**overrides):
    payload = {
        "meeting_date": date.today().isoformat(),
        "meeting_time": "10:00",
        "title": "Weekly sync with client",
        "my_points": "Discussed timeline",
        "meeting_points": "Team raised concerns about scope",
        "decisions": "Extend deadline by a week",
        "notes": "Follow up next Monday",
    }
    payload.update(overrides)
    return payload


def test_create_meeting_valid(auth_client):
    response = auth_client.post("/meetings/create", data=valid_meeting_payload(), follow_redirects=True)
    assert b"Meeting created successfully" in response.data
    assert b"Weekly sync with client" in response.data


def test_create_meeting_without_title_fails(auth_client):
    response = auth_client.post(
        "/meetings/create", data=valid_meeting_payload(title=""), follow_redirects=True
    )
    assert b"Meeting title is required" in response.data


def test_update_meeting(auth_client):
    auth_client.post("/meetings/create", data=valid_meeting_payload())
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute("SELECT id FROM meetings ORDER BY id DESC LIMIT 1").fetchone()
        meeting_id = row["id"]

    response = auth_client.post(
        f"/meetings/{meeting_id}/edit",
        data=valid_meeting_payload(title="Updated meeting title"),
        follow_redirects=True,
    )
    assert b"Meeting updated successfully" in response.data
    assert b"Updated meeting title" in response.data


def test_delete_meeting(auth_client):
    auth_client.post("/meetings/create", data=valid_meeting_payload())
    from database import get_db

    with auth_client.application.app_context():
        row = get_db().execute("SELECT id FROM meetings ORDER BY id DESC LIMIT 1").fetchone()
        meeting_id = row["id"]

    response = auth_client.post(f"/meetings/{meeting_id}/delete", follow_redirects=True)
    assert b"Meeting deleted successfully" in response.data


def test_search_meetings(auth_client):
    auth_client.post("/meetings/create", data=valid_meeting_payload(title="Budget review meeting"))
    auth_client.post("/meetings/create", data=valid_meeting_payload(title="Unrelated standup"))

    response = auth_client.get("/meetings?search=budget")
    assert b"Budget review meeting" in response.data
    assert b"Unrelated standup" not in response.data


def test_meeting_detail_404_for_missing(auth_client):
    response = auth_client.get("/meetings/99999", follow_redirects=True)
    assert b"Meeting not found" in response.data
