from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]
        self.full_name = row["full_name"]
        self.email = row["email"]
        self.is_active_flag = row["is_active"]

    @property
    def is_active(self):
        return bool(self.is_active_flag)

    @staticmethod
    def get_by_id(user_id):
        row = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return User(row) if row else None

    @staticmethod
    def create(username, password, full_name="", email=""):
        db = get_db()
        db.execute(
            """INSERT INTO users (username, password_hash, full_name, email)
               VALUES (?, ?, ?, ?)""",
            (username, generate_password_hash(password), full_name, email),
        )
        db.commit()
        return User.get_by_username(username)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


TASK_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]
TASK_STATUSES = ["TODO", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"]
