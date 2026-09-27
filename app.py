import logging
import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf import CSRFProtect

import database
from config import Config
from models import User
from utils.date_utils import format_date_for_display


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    database.init_app(app)

    app.jinja_env.filters["display_date"] = format_date_for_display
    app.jinja_env.globals["app_name"] = app.config["APP_NAME"]

    csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return User.get_by_id(user_id)

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.email import email_bp
    from routes.meetings import meetings_bp
    from routes.projects import projects_bp
    from routes.reports import reports_bp
    from routes.tasks import tasks_bp
    from routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(email_bp)

    register_error_handlers(app)
    configure_logging(app)

    with app.app_context():
        database.init_db(app)

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables/indexes (safe to re-run)."""
        database.init_db(app)
        print("Database initialized.")

    @app.cli.command("send-scheduled-emails")
    def send_scheduled_emails_command():
        """Send any automatic report emails that are due (for cron)."""
        from services import email_service

        sent = email_service.run_due_schedules()
        print(f"Sent {sent} scheduled email(s).")

    return app


def configure_logging(app):
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.ERROR)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.ERROR)


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500


app = create_app()

if __name__ == "__main__":
    # With debug on, Flask's reloader runs this file twice (a watcher parent
    # and the real server child); only the child sets WERKZEUG_RUN_MAIN, so
    # the scheduler starts exactly once.
    if app.config["EMAIL_SCHEDULER_ENABLED"] and (
        not app.config["DEBUG"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        from services.email_service import start_scheduler

        start_scheduler(app)
    app.run(debug=app.config["DEBUG"])
