import os
import tempfile

import pytest

from app import create_app
from config import Config
from database import init_db
from models import User


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    DEBUG = False


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    TestConfig.DATABASE_PATH = db_path

    application = create_app(TestConfig)

    with application.app_context():
        init_db(application)
        User.create(username="testuser", password="password123", full_name="Test User")

    yield application

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"username": "testuser", "password": "password123"})
    return client
