# app/utils/error_handlers.py
"""JSON error handlers and domain exceptions."""

from flask import jsonify


class UserAlreadyExistsError(Exception):
    """Raised when registering with an email that already exists."""

    pass


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""

    pass


class HabitNotFoundError(Exception):
    """Raised when a habit cannot be found for the current user."""

    pass


class UnauthorizedError(Exception):
    """Raised when a user attempts to access another user's resource."""

    pass


def _error_payload(message, status):
    return jsonify({"error": True, "message": message, "status": status}), status


def register_error_handlers(app):
    """Register HTTP and domain exception handlers."""

    @app.errorhandler(UserAlreadyExistsError)
    def handle_user_exists(err):
        return _error_payload(str(err) or "User already exists", 409)

    @app.errorhandler(InvalidCredentialsError)
    def handle_invalid_creds(err):
        return _error_payload(str(err) or "Invalid credentials", 401)

    @app.errorhandler(HabitNotFoundError)
    def handle_habit_not_found(err):
        return _error_payload(str(err) or "Habit not found", 404)

    @app.errorhandler(UnauthorizedError)
    def handle_unauthorized(err):
        return _error_payload(str(err) or "Unauthorized", 403)

    @app.errorhandler(400)
    def handle_400(err):
        msg = getattr(err, "description", None) or "Bad request"
        return _error_payload(str(msg), 400)

    @app.errorhandler(401)
    def handle_401(err):
        msg = getattr(err, "description", None) or "Unauthorized"
        return _error_payload(str(msg), 401)

    @app.errorhandler(403)
    def handle_403(err):
        msg = getattr(err, "description", None) or "Forbidden"
        return _error_payload(str(msg), 403)

    @app.errorhandler(404)
    def handle_404(err):
        msg = getattr(err, "description", None) or "Not found"
        return _error_payload(str(msg), 404)

    @app.errorhandler(500)
    def handle_500(err):
        msg = getattr(err, "description", None) or "Internal server error"
        return _error_payload(str(msg), 500)
