"""Prepares structured report data. No HTML/rendering logic here so the same
data can feed the reports page, Excel, CSV, and PDF exports.
"""
from services import meeting_service, task_service
from utils.date_utils import format_date_for_display, today


def build_report(user_id, from_date, to_date):
    tasks = task_service.tasks_in_range(user_id, from_date, to_date)
    meetings = meeting_service.meetings_in_range(user_id, from_date, to_date)
    status_counts = task_service.status_counts(user_id, from_date, to_date)

    t = today()
    overdue = sum(
        1
        for row in tasks
        if row["due_date"]
        and row["due_date"] < t.strftime("%Y-%m-%d")
        and row["status"] not in ("COMPLETED", "CANCELLED")
    )

    summary = {
        "total_tasks": len(tasks),
        "completed": status_counts["COMPLETED"],
        "in_progress": status_counts["IN_PROGRESS"],
        "todo": status_counts["TODO"],
        "on_hold": status_counts["ON_HOLD"],
        "cancelled": status_counts["CANCELLED"],
        "overdue": overdue,
        "total_meetings": len(meetings),
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
    }
