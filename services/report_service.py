"""Prepares structured report data. No HTML/rendering logic here so the same
data can feed the reports page, Excel, CSV, and PDF exports.
"""
from services import meeting_service, task_service
from services.task_service import ALL_USERS
from utils.date_utils import format_date_for_display, today


def build_report(owner_id, from_date, to_date, project_id=None):
    """owner_id may be the ALL_USERS sentinel for an admin's cross-user report."""
    tasks = task_service.tasks_in_range(owner_id, from_date, to_date, project_id=project_id)
    meetings = meeting_service.meetings_in_range(owner_id, from_date, to_date, project_id=project_id)
    status_counts = task_service.status_counts(owner_id, from_date, to_date, project_id=project_id)

    t = today()
    overdue = sum(
        1
        for row in tasks
        if row["due_date"]
        and row["due_date"] < t.strftime("%Y-%m-%d")
        and row["status"] not in ("COMPLETED", "CANCELLED")
    )
    total_time_spent = sum(row["time_spent_hours"] or 0 for row in tasks)

    summary = {
        "total_tasks": len(tasks),
        "completed": status_counts["COMPLETED"],
        "in_progress": status_counts["IN_PROGRESS"],
        "todo": status_counts["TODO"],
        "on_hold": status_counts["ON_HOLD"],
        "cancelled": status_counts["CANCELLED"],
        "overdue": overdue,
        "total_meetings": len(meetings),
        "total_time_spent": total_time_spent,
    }

    range_label = (
        f"{format_date_for_display(from_date)} - {format_date_for_display(to_date)}"
        if from_date and to_date
        else "All Time"
    )

    return {
        "tasks": tasks,
        "meetings": meetings,
        "summary": summary,
        "status_counts": status_counts,
        "range_label": range_label,
        "from_date": from_date,
        "to_date": to_date,
        "show_owner": owner_id == ALL_USERS,
    }
