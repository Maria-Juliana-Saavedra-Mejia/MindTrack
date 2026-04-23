# fapi/deps.py
"""JWT and service dependencies for FastAPI routes."""

from typing import Annotated, Optional

import jwt
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.logger import get_logger

logger = get_logger(__name__)

bearer = HTTPBearer(auto_error=False)


class _JSONError(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(message)


def get_jwt_sub(
    request: Request,
    cred: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
) -> str:
    """Return Mongo user id from valid Bearer token."""
    if cred is None or not cred.credentials or cred.scheme.lower() != "bearer":
        raise _JSONError("Missing or invalid Authorization header", 401)
    try:
        payload = jwt.decode(
            cred.credentials,
            request.app.state.jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise _JSONError("Invalid or expired token", 401)
    user_id = payload.get("sub")
    if not user_id:
        raise _JSONError("Invalid or expired token", 401)
    return str(user_id)


def register_bearer_error_handler(app):
    @app.exception_handler(_JSONError)
    def _handle_json_bearer_error(_: Request, exc: _JSONError):
        return JSONResponse(
            content={"error": True, "message": exc.message, "status": exc.status},
            status_code=exc.status,
        )
