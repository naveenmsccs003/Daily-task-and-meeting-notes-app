from database import get_db
from utils.date_utils import format_date_for_db

ALL_USERS = "ALL"


def _apply_filters(where, params, filters):
    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        where.append(
            "(meetings.title LIKE ? OR meetings.my_points LIKE ? OR meetings.meeting_points LIKE ?"
            " OR meetings.decisions LIKE ? OR meetings.notes LIKE ?)"
        )
        params.extend([like, like, like, like, like])

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        where.append("meetings.meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meetings.meeting_date <= ?")
        params.append(format_date_for_db(to_date))

    project_id = filters.get("project_id")
    if project_id:
        where.append("meetings.project_id = ?")
        params.append(project_id)


def _parse_project_id(data):
    raw = (data.get("project_id") or "").strip()
    return int(raw) if raw.isdigit() else None


def list_meetings(owner_id, filters=None, page=1, per_page=25):
    """owner_id is a specific user's id, or the ALL_USERS sentinel for the
    admin oversight view (no owner filter, plus the owner's name joined in).
    """
    filters = filters or {}
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("meetings.user_id = ?")
        params.append(owner_id)
    _apply_filters(where, params, filters)
    where_sql = " AND ".join(where) if where else "1=1"

    total = db.execute(
        f"SELECT COUNT(*) FROM meetings WHERE {where_sql}", params
    ).fetchone()[0]

    offset = max(page - 1, 0) * per_page
    rows = db.execute(
        f"""SELECT meetings.*, users.username AS owner_username, users.full_name AS owner_full_name,
                   projects.name AS project_name, projects.color AS project_color
            FROM meetings
            JOIN users ON users.id = meetings.user_id
            LEFT JOIN projects ON projects.id = meetings.project_id
            WHERE {where_sql}
            ORDER BY meetings.meeting_date DESC, meetings.meeting_time DESC, meetings.id DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()

    return rows, total


def get_meeting(user_id, meeting_id):
    """Strictly owner-scoped lookup, used for edit/delete authorization
    checks — never returns another user's meeting.
    """
    return get_db().execute(
        """SELECT meetings.*, projects.name AS project_name, projects.color AS project_color
           FROM meetings LEFT JOIN projects ON projects.id = meetings.project_id
           WHERE meetings.id = ? AND meetings.user_id = ?""",
        (meeting_id, user_id),
    ).fetchone()


def get_meeting_any(meeting_id):
    """Admin oversight lookup: any meeting regardless of owner, with the
    owner's name joined in for display. Read-only callers only.
    """
    return get_db().execute(
        """SELECT meetings.*, users.username AS owner_username, users.full_name AS owner_full_name,
                  projects.name AS project_name, projects.color AS project_color
           FROM meetings
           JOIN users ON users.id = meetings.user_id
           LEFT JOIN projects ON projects.id = meetings.project_id
           WHERE meetings.id = ?""",
        (meeting_id,),
    ).fetchone()


def create_meeting(user_id, data):
    db = get_db()
    cur = db.execute(
        """INSERT INTO meetings
           (user_id, project_id, meeting_date, meeting_time, title, my_points,
            meeting_points, decisions, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            _parse_project_id(data),
            data["meeting_date"],
            data.get("meeting_time") or None,
            data["title"].strip(),
            data.get("my_points") or None,
            data.get("meeting_points") or None,
            data.get("decisions") or None,
            data.get("notes") or None,
        ),
    )
    db.commit()
    return cur.lastrowid


def update_meeting(user_id, meeting_id, data):
    db = get_db()
    if not get_meeting(user_id, meeting_id):
        return False
    db.execute(
        """UPDATE meetings SET project_id=?, meeting_date=?, meeting_time=?, title=?,
           my_points=?, meeting_points=?, decisions=?, notes=?,
           updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (
            _parse_project_id(data),
            data["meeting_date"],
            data.get("meeting_time") or None,
            data["title"].strip(),
            data.get("my_points") or None,
            data.get("meeting_points") or None,
            data.get("decisions") or None,
            data.get("notes") or None,
            meeting_id,
            user_id,
        ),
    )
    db.commit()
    return True


def delete_meeting(user_id, meeting_id):
    db = get_db()
    cur = db.execute(
        "DELETE FROM meetings WHERE id=? AND user_id=?", (meeting_id, user_id)
    )
    db.commit()
    return cur.rowcount > 0


def meetings_for_date(user_id, date_value):
    db = get_db()
    return db.execute(
        """SELECT * FROM meetings WHERE user_id = ? AND meeting_date = ?
           ORDER BY meeting_time IS NULL, meeting_time ASC""",
        (user_id, format_date_for_db(date_value)),
    ).fetchall()


def count_in_range(owner_id, from_date, to_date):
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("user_id = ?")
        params.append(owner_id)
    if from_date:
        where.append("meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meeting_date <= ?")
        params.append(format_date_for_db(to_date))
    where_sql = " AND ".join(where) if where else "1=1"
    return db.execute(
        f"SELECT COUNT(*) FROM meetings WHERE {where_sql}", params
    ).fetchone()[0]


def meetings_in_range(owner_id, from_date, to_date, project_id=None):
    """owner_id may be the ALL_USERS sentinel for an admin's cross-user report."""
    db = get_db()
    where = []
    params = []
    if owner_id != ALL_USERS:
        where.append("meetings.user_id = ?")
        params.append(owner_id)
    if from_date:
        where.append("meetings.meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meetings.meeting_date <= ?")
        params.append(format_date_for_db(to_date))
    if project_id:
        where.append("meetings.project_id = ?")
        params.append(project_id)
    where_sql = " AND ".join(where) if where else "1=1"
    return db.execute(
        f"""SELECT meetings.*, users.username AS owner_username, users.full_name AS owner_full_name,
                   projects.name AS project_name, projects.color AS project_color
            FROM meetings
            JOIN users ON users.id = meetings.user_id
            LEFT JOIN projects ON projects.id = meetings.project_id
            WHERE {where_sql} ORDER BY meetings.meeting_date DESC, meetings.meeting_time DESC""",
        params,
    ).fetchall()
