from database import get_db
from utils.date_utils import format_date_for_db


def _apply_filters(where, params, filters):
    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        where.append(
            "(title LIKE ? OR my_points LIKE ? OR meeting_points LIKE ?"
            " OR decisions LIKE ? OR notes LIKE ?)"
        )
        params.extend([like, like, like, like, like])

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        where.append("meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meeting_date <= ?")
        params.append(format_date_for_db(to_date))


def list_meetings(user_id, filters=None, page=1, per_page=25):
    filters = filters or {}
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    _apply_filters(where, params, filters)
    where_sql = " AND ".join(where)

    total = db.execute(
        f"SELECT COUNT(*) FROM meetings WHERE {where_sql}", params
    ).fetchone()[0]

    offset = max(page - 1, 0) * per_page
    rows = db.execute(
        f"""SELECT * FROM meetings WHERE {where_sql}
            ORDER BY meeting_date DESC, meeting_time DESC, id DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()

    return rows, total


def get_meeting(user_id, meeting_id):
    return get_db().execute(
        "SELECT * FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id)
    ).fetchone()


def create_meeting(user_id, data):
    db = get_db()
    cur = db.execute(
        """INSERT INTO meetings
           (user_id, meeting_date, meeting_time, title, my_points,
            meeting_points, decisions, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
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
        """UPDATE meetings SET meeting_date=?, meeting_time=?, title=?,
           my_points=?, meeting_points=?, decisions=?, notes=?,
           updated_at=datetime('now')
           WHERE id=? AND user_id=?""",
        (
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


def count_in_range(user_id, from_date, to_date):
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    if from_date:
        where.append("meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meeting_date <= ?")
        params.append(format_date_for_db(to_date))
    where_sql = " AND ".join(where)
    return db.execute(
        f"SELECT COUNT(*) FROM meetings WHERE {where_sql}", params
    ).fetchone()[0]


def meetings_in_range(user_id, from_date, to_date):
    db = get_db()
    where = ["user_id = ?"]
    params = [user_id]
    if from_date:
        where.append("meeting_date >= ?")
        params.append(format_date_for_db(from_date))
    if to_date:
        where.append("meeting_date <= ?")
        params.append(format_date_for_db(to_date))
    where_sql = " AND ".join(where)
    return db.execute(
        f"SELECT * FROM meetings WHERE {where_sql} ORDER BY meeting_date DESC, meeting_time DESC",
        params,
    ).fetchall()
