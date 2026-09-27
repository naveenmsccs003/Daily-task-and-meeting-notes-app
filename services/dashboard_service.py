from services import meeting_service, task_service
from utils.date_utils import today


def get_dashboard_data(user_id, from_date, to_date):
    """Efficient aggregate data for the dashboard: every count/total below
    comes from a SQL GROUP BY or SUM, never by loading full row sets into
    Python.
    """
    status_counts = task_service.status_counts(user_id, from_date, to_date)
    priority_counts = task_service.priority_counts(user_id, from_date, to_date)
    project_breakdown = task_service.project_breakdown(user_id, from_date, to_date)
    completion_trend = task_service.completion_trend(user_id, from_date, to_date)
    hours_totals = task_service.hours_totals(user_id, from_date, to_date)
    overdue = task_service.overdue_count(user_id)
    meeting_count = meeting_service.count_in_range(user_id, from_date, to_date)

    total_tasks = sum(status_counts.values())

    t = today()
    todays_tasks = task_service.tasks_for_date(user_id, t)
    todays_meetings = meeting_service.meetings_for_date(user_id, t)

    return {
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "project_breakdown": project_breakdown,
        "completion_trend": completion_trend,
        "hours_totals": hours_totals,
        "total_tasks": total_tasks,
        "overdue_count": overdue,
        "meeting_count": meeting_count,
        "todays_tasks": todays_tasks,
        "todays_meetings": todays_meetings,
    }
