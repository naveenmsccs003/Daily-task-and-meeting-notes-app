"""Data-access + business logic for tasks. Routes call into this module only;
no SQL lives in routes or templates.
"""
from database import get_db
from utils.date_utils import format_date_for_db, today

SORT_COLUMNS = {
    "date": "task_date",
    "priority": "priority",
    "status": "status",
    "due_date": "due_date",
}


def _apply_filters(where, params, filters):
    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        where.append("(title LIKE ? OR description LIKE ? OR notes LIKE ?)")
        params.extend([like, like, like])

    status = (filters.get("status") or "").strip().upper()
    if status:
        where.append("status = ?")
        params.append(status)

    priority = (filters.get("priority") or "").strip().upper()
    if priority:
        where.append("priority = ?")
        params.append(priority)

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        where.append("task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("task_date <= ?")
        params.append(format_date_for_db(to_date))


def list_tasks(user_id, filters=None, page=1, per_page=25, sort="date", sort_dir="desc"):
    filters = filters or {}
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    _apply_filters(where, params, filters)
    where_sql = " AND ".join(where)

    sort_col = SORT_COLUMNS.get(sort, "task_date")
    sort_dir = "ASC" if sort_dir == "asc" else "DESC"

    total = db.execute(
        f"SELECT COUNT(*) FROM tasks WHERE {where_sql}", params
    ).fetchone()[0]

    offset = max(page - 1, 0) * per_page
    rows = db.execute(
        f"""SELECT * FROM tasks WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir}, task_time {sort_dir}, id DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()

    return rows, total


def get_task(user_id, task_id):
    return get_db().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()


def create_task(user_id, data):
    db = get_db()
    status = data["status"].upper()
    completed_at = None
    if status == "COMPLETED":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]

    cur = db.execute(
        """INSERT INTO tasks
           (user_id, task_date, task_time, title, description, priority,
            status, due_date, notes, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            data["task_date"],
            data.get("task_time") or None,
            data["title"].strip(),
            data.get("description") or None,
            data["priority"].upper(),
            status,
            data.get("due_date") or None,
            data.get("notes") or None,
            completed_at,
        ),
    )
    db.commit()
    return cur.lastrowid


def update_task(user_id, task_id, data):
    db = get_db()
    existing = get_task(user_id, task_id)
    if not existing:
        return False

    new_status = data["status"].upper()
    completed_at = existing["completed_at"]
    if new_status == "COMPLETED" and existing["status"] != "COMPLETED":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]
    elif new_status != "COMPLETED":
        completed_at = None

    db.execute(
        """UPDATE tasks SET task_date=?, task_time=?, title=?, description=?,
           priority=?, status=?, due_date=?, notes=?, completed_at=?,
           updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (
            data["task_date"],
            data.get("task_time") or None,
            data["title"].strip(),
            data.get("description") or None,
            data["priority"].upper(),
            new_status,
            data.get("due_date") or None,
            data.get("notes") or None,
            completed_at,
            task_id,
            user_id,
        ),
    )
    db.commit()
    return True


def update_status(user_id, task_id, status):
    db = get_db()
    existing = get_task(user_id, task_id)
    if not existing:
        return False

    completed_at = existing["completed_at"]
    if status == "COMPLETED" and existing["status"] != "COMPLETED":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]
    elif status != "COMPLETED":
        completed_at = None

    db.execute(
        """UPDATE tasks SET status=?, completed_at=?, updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (status, completed_at, task_id, user_id),
    )
    db.commit()
    return True


def delete_task(user_id, task_id):
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    db.commit()
    return cur.rowcount > 0


def status_counts(user_id, from_date=None, to_date=None):
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    if from_date:
        where.append("task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("task_date <= ?")
        params.append(format_date_for_db(to_date))
    where_sql = " AND ".join(where)

    rows = db.execute(
        f"SELECT status, COUNT(*) as cnt FROM tasks WHERE {where_sql} GROUP BY status",
        params,
    ).fetchall()
    counts = {"TODO": 0, "IN_PROGRESS": 0, "ON_HOLD": 0, "COMPLETED": 0, "CANCELLED": 0}
    for row in rows:
        counts[row["status"]] = row["cnt"]
    return counts


def overdue_count(user_id):
    db = get_db()
    row = db.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE user_id = ? AND due_date IS NOT NULL AND due_date != ''
             AND due_date < ? AND status NOT IN ('COMPLETED', 'CANCELLED')""",
        (user_id, format_date_for_db(today())),
    ).fetchone()
    return row[0]


def tasks_for_date(user_id, date_value):
    db = get_db()
    return db.execute(
        """SELECT * FROM tasks WHERE user_id = ? AND task_date = ?
           ORDER BY task_time IS NULL, task_time ASC""",
        (user_id, format_date_for_db(date_value)),
    ).fetchall()


def tasks_in_range(user_id, from_date, to_date):
    """All tasks (no pagination) for report/export generation."""
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    if from_date:
        where.append("task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("task_date <= ?")
        params.append(format_date_for_db(to_date))
    where_sql = " AND ".join(where)
    return db.execute(
        f"SELECT * FROM tasks WHERE {where_sql} ORDER BY task_date DESC, task_time DESC",
        params,
    ).fetchall()
