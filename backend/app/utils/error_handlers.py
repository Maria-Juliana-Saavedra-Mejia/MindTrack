# app/utils/error_handlers.py
"""Domain exceptions for services and FastAPI exception_handlers."""


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
