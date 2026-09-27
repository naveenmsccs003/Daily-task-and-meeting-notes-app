from functools import wraps

from flask import abort, current_app
from flask_login import current_user

from utils.helpers import json_error, wants_json


def admin_required(view):
    """Restrict a route to admin-role users. Apply after @login_required so
    an unauthenticated request is sent to the login page rather than a 403.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def handle_errors(default_message="Something went wrong. Please try again."):
    """Wrap a route so unexpected exceptions never leak a stack trace to the
    client. Flask's app-level error handlers still cover uncaught cases; this
    is for routes that need a clean JSON error response for AJAX callers.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            try:
                return view(*args, **kwargs)
            except ValueError as exc:
                if wants_json():
                    return json_error(str(exc))
                raise
            except Exception:
                current_app.logger.exception("Unhandled error in %s", view.__name__)
                if wants_json():
                    return json_error(default_message, status=500)
                raise

        return wrapped

    return decorator
