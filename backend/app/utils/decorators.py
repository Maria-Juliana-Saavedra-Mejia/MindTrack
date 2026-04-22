# app/utils/decorators.py
"""Flask decorators for authentication."""

from functools import wraps

import jwt
from flask import g, jsonify, request, current_app


def jwt_required(fn):
    """Validate JWT from Authorization header and set g.user_id."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Missing or invalid Authorization header",
                        "status": 401,
                    }
                ),
                401,
            )
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Missing token",
                        "status": 401,
                    }
                ),
                401,
            )
        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
            )
            user_id = payload.get("sub")
            if not user_id:
                raise jwt.InvalidTokenError()
            g.user_id = str(user_id)
        except jwt.PyJWTError:
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Invalid or expired token",
                        "status": 401,
                    }
                ),
                401,
            )
        return fn(*args, **kwargs)

    return wrapper
