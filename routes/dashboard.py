from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services.dashboard_service import get_dashboard_data
from utils.date_utils import format_date_for_db, get_period_dates

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    period = request.args.get("period", "month")
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    try:
        from_date, to_date = get_period_dates(period, start, end)
    except ValueError as exc:
        flash(str(exc), "danger")
        period = "month"
        from_date, to_date = get_period_dates(period)

    data = get_dashboard_data(current_user.id, from_date, to_date)

    return render_template(
        "dashboard.html",
        data=data,
        period=period,
        from_date=format_date_for_db(from_date) if from_date else "",
        to_date=format_date_for_db(to_date) if to_date else "",
    )
