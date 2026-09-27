from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from database import get_db
from models import User
from services import email_service

TZ = ZoneInfo("Asia/Kolkata")


class FakeSMTP:
    """Stands in for smtplib.SMTP and records every message sent."""

    sent = []
    fail_with = None

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, username, password):
        pass

    def send_message(self, msg):
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with
        FakeSMTP.sent.append(msg)


@pytest.fixture
def mail(app, monkeypatch):
    app.config.update(MAIL_SERVER="smtp.test", MAIL_USERNAME="bot@test.com", MAIL_PASSWORD="x")
    FakeSMTP.sent = []
    FakeSMTP.fail_with = None
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def _bodies(msg):
    text = msg.get_body(preferencelist=("plain",)).get_content()
    html = msg.get_body(preferencelist=("html",)).get_content()
    return text, html


def _add_data(client, day="2026-09-27"):
    client.post("/tasks/create", data={
        "task_date": day, "task_time": "09:00", "title": "Write <spec>", "priority": "HIGH",
        "status": "IN_PROGRESS", "notes": "- first note\n- second note",
    })
    client.post("/meetings/create", data={
        "meeting_date": day, "meeting_time": "10:00", "title": "Standup",
        "my_points": "Finished login page\nStarted reports", "meeting_points": "1. Release on Friday",
        "decisions": "* Ship it",
    })


def test_email_page_requires_login(client):
    assert client.get("/email").status_code == 302


def test_email_page_shows_not_configured_warning(auth_client):
    r = auth_client.get("/email")
    assert r.status_code == 200
    assert b"Email is not set up yet" in r.data
    for label in (b"Daily", b"Weekly", b"Monthly", b"Every 6 Months", b"Yearly"):
        assert label in r.data


def test_send_without_config_fails_and_is_logged(auth_client, app):
    r = auth_client.post("/email/send", data={"period": "today", "recipients": "a@b.com", "tasks": "on"})
    assert b"Email is not set up yet" in r.data
    with app.app_context():
        row = get_db().execute("SELECT * FROM email_log").fetchone()
    assert row["success"] == 0


def test_send_report_point_by_point(auth_client, mail):
    _add_data(auth_client)
    r = auth_client.post("/email/send", data={
        "period": "custom", "start_date": "2026-09-01", "end_date": "2026-09-30",
        "recipients": "boss@x.com, me@x.com", "status": "on", "tasks": "on", "meetings": "on",
    }, follow_redirects=True)
    assert b"Report emailed to boss@x.com, me@x.com" in r.data
    assert len(mail.sent) == 1
    msg = mail.sent[0]
    assert msg["To"] == "boss@x.com, me@x.com"
    assert "01 Sep 2026 - 30 Sep 2026" in msg["Subject"]
    text, html = _bodies(msg)
    assert "1. Write <spec>" in text
    assert "Status: In Progress | Priority: High" in text
    assert "   - Note: first note" in text and "   - Note: second note" in text
    assert "1) Finished login page" in text and "2) Started reports" in text
    assert "1) Release on Friday" in text and "1) Ship it" in text
    assert "In Progress: 1" in text
    assert "Write &lt;spec&gt;" in html and "<spec>" not in html
    assert b"Sent" in auth_client.get("/email").data


def test_send_only_selected_sections(auth_client, mail):
    _add_data(auth_client)
    auth_client.post("/email/send", data={"period": "all", "recipients": "a@b.com", "meetings": "on"})
    text, _ = _bodies(mail.sent[0])
    assert "MEETINGS" in text and "TASKS" not in text and "TASK STATUS" not in text


def test_send_validation_errors(auth_client, mail):
    r = auth_client.post("/email/send", data={"period": "today", "recipients": "not-an-email"})
    assert b"Invalid email address" in r.data
    assert b"Choose at least one" in r.data
    r = auth_client.post("/email/send", data={"period": "custom", "recipients": "a@b.com", "tasks": "on"})
    assert b"Both From Date and To Date are required" in r.data
    assert mail.sent == []


def test_smtp_failure_shown_and_logged(auth_client, mail, app):
    import smtplib
    mail.fail_with = smtplib.SMTPException("server down")
    r = auth_client.post("/email/send", data={"period": "today", "recipients": "a@b.com", "tasks": "on"})
    assert b"Could not send email" in r.data
    with app.app_context():
        assert get_db().execute("SELECT success FROM email_log").fetchone()[0] == 0


def test_email_only_contains_own_data(app, auth_client, mail):
    with app.app_context():
        User.create(username="other", password="password123")
    other = app.test_client()
    other.post("/login", data={"username": "other", "password": "password123"})
    other.post("/tasks/create", data={"task_date": "2026-09-27", "title": "Secret task", "priority": "LOW", "status": "TODO"})
    auth_client.post("/email/send", data={"period": "all", "recipients": "a@b.com", "tasks": "on"})
    text, _ = _bodies(mail.sent[0])
    assert "Secret task" not in text


@pytest.mark.parametrize("freq,day,expected", [
    ("daily", date(2026, 9, 27), (date(2026, 9, 27), date(2026, 9, 27))),
    ("weekly", date(2026, 9, 23), (date(2026, 9, 21), date(2026, 9, 27))),
    ("monthly", date(2026, 2, 10), (date(2026, 2, 1), date(2026, 2, 28))),
    ("6months", date(2026, 3, 5), (date(2026, 1, 1), date(2026, 6, 30))),
    ("6months", date(2026, 11, 5), (date(2026, 7, 1), date(2026, 12, 31))),
    ("yearly", date(2026, 5, 5), (date(2026, 1, 1), date(2026, 12, 31))),
])
def test_period_containing(freq, day, expected):
    assert email_service.period_containing(freq, day) == expected


def test_due_period_before_and_after_send_hour(app):
    with app.app_context():
        app.config["EMAIL_SEND_HOUR"] = 18
        # Sunday 27 Sep 2026: before 18:00 the latest due week is the previous one.
        assert email_service.due_period("weekly", datetime(2026, 9, 27, 17, 0, tzinfo=TZ))[0] == date(2026, 9, 14)
        assert email_service.due_period("weekly", datetime(2026, 9, 27, 18, 0, tzinfo=TZ))[0] == date(2026, 9, 21)
        assert email_service.due_period("daily", datetime(2026, 9, 27, 9, 0, tzinfo=TZ))[0] == date(2026, 9, 26)


def _enable_daily(client, **extra):
    data = {"daily_active": "on", "daily_recipients": "me@x.com", "daily_tasks": "on", "daily_status": "on"}
    data.update(extra)
    return client.post("/email/schedules", data=data, follow_redirects=True)


def test_save_schedule_and_validation(auth_client, app):
    r = _enable_daily(auth_client, daily_recipients="")
    assert b"Enter at least one email address" in r.data
    r = _enable_daily(auth_client)
    assert b"Automatic email settings saved" in r.data
    with app.app_context():
        row = get_db().execute("SELECT * FROM email_schedules WHERE frequency='daily'").fetchone()
    assert row["is_active"] == 1 and row["recipients"] == "me@x.com"
    assert row["include_tasks"] == 1 and row["include_meetings"] == 0


def test_scheduler_sends_once_per_period(auth_client, app, mail, monkeypatch):
    enabled_at = datetime(2026, 9, 27, 12, 0, tzinfo=TZ)
    monkeypatch.setattr(email_service, "_now", lambda: enabled_at)
    _enable_daily(auth_client)
    with app.app_context():
        # Enabling must not immediately send yesterday's report.
        assert email_service.run_due_schedules(now=enabled_at) == 0
        evening = datetime(2026, 9, 27, 18, 5, tzinfo=TZ)
        assert email_service.run_due_schedules(now=evening) == 1
        assert email_service.run_due_schedules(now=evening) == 0
        # App was off all of the next day: catches up the following morning.
        assert email_service.run_due_schedules(now=datetime(2026, 9, 29, 8, 0, tzinfo=TZ)) == 1
    assert len(mail.sent) == 2
    assert mail.sent[0]["Subject"].startswith("Daily Report: 27 Sep 2026")
    assert mail.sent[1]["Subject"].startswith("Daily Report: 28 Sep 2026")


def test_scheduler_retries_failed_send_after_an_hour(auth_client, app, mail, monkeypatch):
    import smtplib
    monkeypatch.setattr(email_service, "_now", lambda: datetime(2026, 9, 27, 12, 0, tzinfo=TZ))
    _enable_daily(auth_client)
    mail.fail_with = smtplib.SMTPException("down")
    with app.app_context():
        assert email_service.run_due_schedules(now=datetime(2026, 9, 27, 18, 5, tzinfo=TZ)) == 0
        mail.fail_with = None
        assert email_service.run_due_schedules(now=datetime(2026, 9, 27, 18, 30, tzinfo=TZ)) == 0
        assert email_service.run_due_schedules(now=datetime(2026, 9, 27, 19, 10, tzinfo=TZ)) == 1


def test_scheduler_does_nothing_without_mail_config(auth_client, app):
    _enable_daily(auth_client)
    with app.app_context():
        assert email_service.run_due_schedules(now=datetime(2030, 1, 1, 23, 0, tzinfo=TZ)) == 0


def test_send_now_uses_form_values(auth_client, mail):
    _add_data(auth_client)
    r = auth_client.post("/email/schedules/monthly/send", data={
        "monthly_recipients": "now@x.com", "monthly_meetings": "on",
    }, follow_redirects=True)
    assert b"Monthly Report" in r.data and b"now@x.com" in r.data
    assert mail.sent[0]["To"] == "now@x.com"
    r = auth_client.post("/email/schedules/bogus/send", data={}, follow_redirects=True)
    assert b"Unknown email frequency" in r.data


def test_to_points_strips_bullets():
    assert email_service.to_points("- a\n\n* b\n1. c\n2) d\n• e\n plain ") == ["a", "b", "c", "d", "e", "plain"]


def test_parse_recipients():
    assert email_service.parse_recipients("a@b.com; c@d.com a@b.com") == (["a@b.com", "c@d.com"], None)
    assert email_service.parse_recipients("")[1]
    assert email_service.parse_recipients("a@b.com\nBcc: x@y.com")[1]
