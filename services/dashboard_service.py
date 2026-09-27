from services import meeting_service, task_service
from utils.date_utils import today


def get_dashboard_data(user_id, from_date, to_date):
    """Efficient aggregate data for the dashboard: status counts via SQL
    GROUP BY (not loading full row sets into Python).
    """
    status_counts = task_service.status_counts(user_id, from_date, to_date)
    overdue = task_service.overdue_count(user_id)
    meeting_count = meeting_service.count_in_range(user_id, from_date, to_date)

    total_tasks = sum(status_counts.values())

    t = today()
    todays_tasks = task_service.tasks_for_date(user_id, t)
    todays_meetings = meeting_service.meetings_for_date(user_id, t)

    return {
        "status_counts": status_counts,
        "total_tasks": total_tasks,
        "overdue_count": overdue,
        "meeting_count": meeting_count,
        "todays_tasks": todays_tasks,
        "todays_meetings": todays_meetings,
    }
