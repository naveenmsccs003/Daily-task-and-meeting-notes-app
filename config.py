import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_NAME = "Moraccle Task & Meeting Tracker"
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-value")
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "instance", "database.db")
    )
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")

    # Outgoing email (SMTP). Leave MAIL_SERVER empty to disable sending.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")

    # Automatic (scheduled) report emails: the background checker runs while
    # `python app.py` is running; `flask send-scheduled-emails` does the same
    # check once, for use from cron/Task Scheduler instead.
    EMAIL_SCHEDULER_ENABLED = os.environ.get("EMAIL_SCHEDULER_ENABLED", "True").lower() == "true"
    EMAIL_SEND_HOUR = int(os.environ.get("EMAIL_SEND_HOUR", 18))
    EMAIL_CHECK_INTERVAL_SECONDS = int(os.environ.get("EMAIL_CHECK_INTERVAL_SECONDS", 300))

    TASKS_PER_PAGE = 25
    MEETINGS_PER_PAGE = 25

    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
