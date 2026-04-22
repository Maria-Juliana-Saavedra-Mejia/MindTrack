# fapi/exception_handlers.py
"""Map domain exceptions to JSON like the legacy Flask app."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.error_handlers import (
    HabitNotFoundError,
    InvalidCredentialsError,
    UnauthorizedError,
    UserAlreadyExistsError,
)


def _err(message: str, status: int):
    return JSONResponse(
        content={"error": True, "message": message, "status": status},
        status_code=status,
    )


def register_domain_handlers(app):
    @app.exception_handler(UserAlreadyExistsError)
    def user_exists(_: Request, exc: UserAlreadyExistsError):
        return _err(str(exc) or "User already exists", 409)

    @app.exception_handler(InvalidCredentialsError)
    def bad_creds(_: Request, exc: InvalidCredentialsError):
        return _err(str(exc) or "Invalid credentials", 401)

    @app.exception_handler(HabitNotFoundError)
    def habit_404(_: Request, exc: HabitNotFoundError):
        return _err(str(exc) or "Habit not found", 404)

    @app.exception_handler(UnauthorizedError)
    def unauth(_: Request, exc: UnauthorizedError):
        return _err(str(exc) or "Unauthorized", 403)
