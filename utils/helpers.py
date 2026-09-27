import re
from datetime import datetime

from flask import jsonify, request


def wants_json():
    """True for fetch/AJAX calls (quick status update, etc.)."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]


def json_success(message, **extra):
    payload = {"success": True, "message": message}
    payload.update(extra)
    return jsonify(payload)


def json_error(message, status=400, **extra):
    payload = {"success": False, "message": message}
    payload.update(extra)
    response = jsonify(payload)
    response.status_code = status
    return response


_SAFE_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def safe_export_filename(prefix, extension):
    """Application-controlled filename; never derived from raw user input."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = _SAFE_CHARS.sub("_", prefix)[:50]
    return f"{prefix}_{stamp}.{extension}"
