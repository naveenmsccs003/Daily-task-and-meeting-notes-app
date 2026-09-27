"""Projects are a shared taxonomy: any logged-in user can create, edit, and
archive them, and tag their own tasks/meetings with one. They are not
per-user private data like tasks/meetings.
"""
from database import get_db


def list_projects(include_archived=True):
    db = get_db()
    if include_archived:
        return db.execute("SELECT * FROM projects ORDER BY is_active DESC, name ASC").fetchall()
    return db.execute(
        "SELECT * FROM projects WHERE is_active = 1 ORDER BY name ASC"
    ).fetchall()


def get_project(project_id):
    return get_db().execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()


def get_by_name(name):
    return get_db().execute(
        "SELECT * FROM projects WHERE name = ?", (name,)
    ).fetchone()


def create_project(name, description, color, created_by):
    db = get_db()
    cur = db.execute(
        """INSERT INTO projects (name, description, color, created_by)
           VALUES (?, ?, ?, ?)""",
        (name.strip(), description or None, color or "#4f46e5", created_by),
    )
    db.commit()
    return cur.lastrowid


def update_project(project_id, name, description, color):
    db = get_db()
    db.execute(
        """UPDATE projects SET name=?, description=?, color=?, updated_at=datetime('now')
           WHERE id=?""",
        (name.strip(), description or None, color or "#4f46e5", project_id),
    )
    db.commit()


def set_active(project_id, is_active):
    db = get_db()
    db.execute(
        "UPDATE projects SET is_active=?, updated_at=datetime('now') WHERE id=?",
        (1 if is_active else 0, project_id),
    )
    db.commit()


def task_count(project_id):
    row = get_db().execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()
    return row[0]


def meeting_count(project_id):
    row = get_db().execute(
        "SELECT COUNT(*) FROM meetings WHERE project_id = ?", (project_id,)
    ).fetchone()
    return row[0]
