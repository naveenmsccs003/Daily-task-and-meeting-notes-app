"""Data-access + business logic for tasks. Routes call into this module only;
no SQL lives in routes or templates.
"""
from database import get_db
from utils.date_utils import format_date_for_db, today

PRIORITY_ORDER_SQL = (
    "CASE tasks.priority WHEN 'LOW' THEN 1 WHEN 'MEDIUM' THEN 2 "
    "WHEN 'HIGH' THEN 3 WHEN 'URGENT' THEN 4 ELSE 0 END"
)
STATUS_ORDER_SQL = (
    "CASE tasks.status WHEN 'TODO' THEN 1 WHEN 'IN_PROGRESS' THEN 2 "
    "WHEN 'ON_HOLD' THEN 3 WHEN 'COMPLETED' THEN 4 WHEN 'CANCELLED' THEN 5 ELSE 0 END"
)

# Values here are hardcoded, whitelisted SQL fragments (never derived from
# the untrusted `sort` request param) so building ORDER BY with an f-string
# below is safe from injection; priority/status use a CASE ranking instead
# of a plain column so "High" sorts above "Low", not alphabetically.
SORT_COLUMNS = {
    "date": "tasks.task_date",
    "priority": PRIORITY_ORDER_SQL,
    "status": STATUS_ORDER_SQL,
    "due_date": "tasks.due_date",
}


def _apply_filters(where, params, filters):
    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        where.append("(tasks.title LIKE ? OR tasks.description LIKE ? OR tasks.notes LIKE ?)")
        params.extend([like, like, like])

    status = (filters.get("status") or "").strip().upper()
    if status:
        where.append("tasks.status = ?")
        params.append(status)

    priority = (filters.get("priority") or "").strip().upper()
    if priority:
        where.append("tasks.priority = ?")
        params.append(priority)

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        where.append("tasks.task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("tasks.task_date <= ?")
        params.append(format_date_for_db(to_date))

    project_id = filters.get("project_id")
    if project_id:
        where.append("tasks.project_id = ?")
        params.append(project_id)


ALL_USERS = "ALL"


def list_tasks(owner_id, filters=None, page=1, per_page=25, sort="date", sort_dir="desc"):
    """owner_id is a specific user's id, or the ALL_USERS sentinel for the
    admin oversight view (no owner filter, plus the owner's name joined in).
    """
    filters = filters or {}
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("tasks.user_id = ?")
        params.append(owner_id)
    _apply_filters(where, params, filters)
    where_sql = " AND ".join(where) if where else "1=1"

    sort_col = SORT_COLUMNS.get(sort, "tasks.task_date")
    sort_dir = "ASC" if sort_dir == "asc" else "DESC"

    total = db.execute(
        f"SELECT COUNT(*) FROM tasks WHERE {where_sql}", params
    ).fetchone()[0]

    offset = max(page - 1, 0) * per_page
    rows = db.execute(
        f"""SELECT tasks.*, users.username AS owner_username, users.full_name AS owner_full_name,
                   projects.name AS project_name, projects.color AS project_color
            FROM tasks
            JOIN users ON users.id = tasks.user_id
            LEFT JOIN projects ON projects.id = tasks.project_id
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir}, tasks.task_time {sort_dir}, tasks.id DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()

    return rows, total


def get_task(user_id, task_id):
    """Strictly owner-scoped lookup, used for edit/delete/status-update
    authorization checks — never returns another user's task.
    """
    return get_db().execute(
        """SELECT tasks.*, projects.name AS project_name, projects.color AS project_color
           FROM tasks LEFT JOIN projects ON projects.id = tasks.project_id
           WHERE tasks.id = ? AND tasks.user_id = ?""",
        (task_id, user_id),
    ).fetchone()


def get_task_any(task_id):
    """Admin oversight lookup: any task regardless of owner, with the
    owner's name joined in for display. Read-only callers only.
    """
    return get_db().execute(
        """SELECT tasks.*, users.username AS owner_username, users.full_name AS owner_full_name,
                  projects.name AS project_name, projects.color AS project_color
           FROM tasks
           JOIN users ON users.id = tasks.user_id
           LEFT JOIN projects ON projects.id = tasks.project_id
           WHERE tasks.id = ?""",
        (task_id,),
    ).fetchone()


def _parse_project_id(data):
    raw = (data.get("project_id") or "").strip()
    return int(raw) if raw.isdigit() else None


def _parse_time_spent(data):
    raw = (data.get("time_spent_hours") or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def create_task(user_id, data):
    db = get_db()
    status = data["status"].upper()
    completed_at = None
    if status == "COMPLETED":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]

    cur = db.execute(
        """INSERT INTO tasks
           (user_id, project_id, task_date, task_time, title, description, priority,
            status, due_date, notes, time_spent_hours, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            _parse_project_id(data),
            data["task_date"],
            data.get("task_time") or None,
            data["title"].strip(),
            data.get("description") or None,
            data["priority"].upper(),
            status,
            data.get("due_date") or None,
            data.get("notes") or None,
            _parse_time_spent(data),
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
        """UPDATE tasks SET project_id=?, task_date=?, task_time=?, title=?, description=?,
           priority=?, status=?, due_date=?, notes=?, time_spent_hours=?, completed_at=?,
           updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (
            _parse_project_id(data),
            data["task_date"],
            data.get("task_time") or None,
            data["title"].strip(),
            data.get("description") or None,
            data["priority"].upper(),
            new_status,
            data.get("due_date") or None,
            data.get("notes") or None,
            _parse_time_spent(data),
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


def status_counts(owner_id, from_date=None, to_date=None, project_id=None):
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("user_id = ?")
        params.append(owner_id)
    if from_date:
        where.append("task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("task_date <= ?")
        params.append(format_date_for_db(to_date))
    if project_id:
        where.append("project_id = ?")
        params.append(project_id)
    where_sql = " AND ".join(where) if where else "1=1"

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


def tasks_in_range(owner_id, from_date, to_date, project_id=None):
    """All tasks (no pagination) for report/export generation. owner_id may
    be the ALL_USERS sentinel for an admin's cross-user report.
    """
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("tasks.user_id = ?")
        params.append(owner_id)
    if from_date:
        where.append("tasks.task_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("tasks.task_date <= ?")
        params.append(format_date_for_db(to_date))
    if project_id:
        where.append("tasks.project_id = ?")
        params.append(project_id)
    where_sql = " AND ".join(where) if where else "1=1"
    return db.execute(
        f"""SELECT tasks.*, users.username AS owner_username, users.full_name AS owner_full_name,
                   projects.name AS project_name, projects.color AS project_color
            FROM tasks
            JOIN users ON users.id = tasks.user_id
            LEFT JOIN projects ON projects.id = tasks.project_id
            WHERE {where_sql} ORDER BY tasks.task_date DESC, tasks.task_time DESC""",
        params,
    ).fetchall()
