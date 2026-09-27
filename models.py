from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db

ROLES = ["user", "admin"]


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]
        self.full_name = row["full_name"]
        self.email = row["email"]
        self.role = row["role"]
        self.is_active_flag = row["is_active"]
        self.created_at = row["created_at"]

    @property
    def is_active(self):
        return bool(self.is_active_flag)

    @property
    def is_admin(self):
        return self.role == "admin"

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
    def get_all():
        rows = get_db().execute(
            "SELECT * FROM users ORDER BY username ASC"
        ).fetchall()
        return [User(row) for row in rows]

    @staticmethod
    def count_active_admins():
        row = get_db().execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
        ).fetchone()
        return row[0]

    @staticmethod
    def create(username, password, full_name="", email="", role="user"):
        db = get_db()
        db.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role)
               VALUES (?, ?, ?, ?, ?)""",
            (username, generate_password_hash(password), full_name, email, role),
        )
        db.commit()
        return User.get_by_username(username)

    @staticmethod
    def update_profile(user_id, full_name, email, role, is_active):
        db = get_db()
        db.execute(
            """UPDATE users SET full_name = ?, email = ?, role = ?, is_active = ?,
               updated_at = datetime('now') WHERE id = ?""",
            (full_name, email, role, 1 if is_active else 0, user_id),
        )
        db.commit()

    @staticmethod
    def set_password(user_id, new_password):
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )
        db.commit()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


TASK_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]
TASK_STATUSES = ["TODO", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"]
