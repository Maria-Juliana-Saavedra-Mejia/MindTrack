# fapi/exception_handlers.py
"""Map domain exceptions to consistent JSON responses."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from app.config import Config
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


def _validation_errors_payload(errors):
    """Short list for clients; full `loc`/`msg` from Pydantic."""
    out = []
    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", ()) if x != "body")
        out.append({"field": loc or "body", "message": err.get("msg", "invalid")})
    return out


def register_domain_handlers(app):

    @app.exception_handler(RequestValidationError)
    def validation_error(_: Request, exc: RequestValidationError):
        payload = {
            "error": True,
            "message": "Invalid request body",
            "status": 422,
            "details": _validation_errors_payload(exc.errors()),
        }
        if Config._runtime_env_name() != "production":
            payload["errors"] = exc.errors()
        return JSONResponse(content=payload, status_code=422)

    @app.exception_handler(DuplicateKeyError)
    def duplicate_key(_: Request, exc: DuplicateKeyError):
        return _err("A record with this unique field already exists", 409)

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
