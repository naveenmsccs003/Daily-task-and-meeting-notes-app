import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-value")
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "instance", "database.db")
    )
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")

    TASKS_PER_PAGE = 25
    MEETINGS_PER_PAGE = 25

    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
