"""Optional development seed data: a handful of tasks and meetings across
different dates/statuses/priorities so the dashboard is immediately
testable. Never run this against a production database.

Usage:
    python seed_data.py
"""
from datetime import timedelta

from app import create_app
from database import get_db
from models import User
from utils.date_utils import format_date_for_db, today

TASKS = [
    (0, "09:00", "Prepare weekly status report", "HIGH", "IN_PROGRESS", 0, "Include client feedback section"),
    (0, "11:30", "Review pull requests", "MEDIUM", "TODO", 0, ""),
    (-1, "14:00", "Client call - project Alpha", "URGENT", "COMPLETED", -1, "Discussed timeline"),
    (-2, "10:00", "Update project documentation", "LOW", "COMPLETED", -2, ""),
    (-3, "09:30", "Fix login bug", "HIGH", "COMPLETED", -3, "Resolved session timeout issue"),
    (1, "15:00", "Plan sprint retrospective", "MEDIUM", "TODO", 3, ""),
    (-5, "13:00", "Vendor negotiation", "HIGH", "ON_HOLD", -1, "Waiting on legal review"),
    (2, "16:00", "Prepare client presentation", "URGENT", "TODO", 2, ""),
    (-1, "17:00", "Cancel outdated subscription", "LOW", "CANCELLED", "", ""),
]

MEETINGS = [
    (0, "10:00", "Daily Standup", "Reported blockers on API integration", "Team discussed sprint velocity", "Move story to next sprint", ""),
    (0, "15:30", "Client Sync - Project Alpha", "Presented current progress", "Client requested UI changes", "Extend deadline by one week", "Follow up email sent"),
    (-2, "11:00", "Sprint Planning", "Estimated backlog items", "Team agreed on sprint goals", "Sprint goal finalized", ""),
    (-4, "09:00", "Architecture Review", "Proposed caching layer", "Reviewed database schema", "Adopt Redis for caching", ""),
]


def main():
    app = create_app()
    with app.app_context():
        user = User.get_by_username("admin")
        if not user:
            print("Run init_db.py first to create the admin user.")
            return

        db = get_db()
        t = today()

        for offset, time_, title, priority, status, due_offset, notes in TASKS:
            task_date = format_date_for_db(t + timedelta(days=offset))
            due_date = format_date_for_db(t + timedelta(days=due_offset)) if due_offset != "" else None
            db.execute(
                """INSERT INTO tasks (user_id, task_date, task_time, title, description,
                   priority, status, due_date, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user.id, task_date, time_, title, "", priority, status, due_date, notes),
            )

        for offset, time_, title, my_points, meeting_points, decisions, notes in MEETINGS:
            meeting_date = format_date_for_db(t + timedelta(days=offset))
            db.execute(
                """INSERT INTO meetings (user_id, meeting_date, meeting_time, title,
                   my_points, meeting_points, decisions, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user.id, meeting_date, time_, title, my_points, meeting_points, decisions, notes),
            )

        db.commit()
        print(f"Seeded {len(TASKS)} tasks and {len(MEETINGS)} meetings for user 'admin'.")


if __name__ == "__main__":
    main()
