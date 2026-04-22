# backend/app/routes/auth.py
"""Authentication routes."""

from flask import Blueprint, current_app, jsonify, request

from app.utils.decorators import jwt_required
from app.utils.logger import get_logger

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
logger = get_logger(__name__)


def get_auth_service():
    return current_app.extensions["auth_service"]


@bp.route("/register", methods=["POST"])
def register():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        logger.info("Register attempt for %s", payload.get("email"))
        get_auth_service().register_user(payload)
        token_bundle = get_auth_service().login_user(
            payload.get("email", ""), payload.get("password", "")
        )
        return jsonify(token_bundle), 201
    except ValueError as exc:
        logger.warning("Register validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("Register failed: %s", exc)
        raise


@bp.route("/login", methods=["POST"])
def login():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        logger.info("Login attempt for %s", payload.get("email"))
        result = get_auth_service().login_user(
            payload.get("email", ""), payload.get("password", "")
        )
        return jsonify(result), 200
    except Exception as exc:
        logger.warning("Login failed: %s", exc)
        raise


@bp.route("/logout", methods=["POST"])
def logout():
    try:
        logger.info("Logout request")
        return jsonify({"success": True, "message": "Logged out"}), 200
    except Exception as exc:
        logger.exception("Logout error: %s", exc)
        raise


@bp.route("/me", methods=["GET"])
@jwt_required
def me():
    try:
        from flask import g

        logger.info("Profile request for user %s", g.user_id)
        user = get_auth_service().get_user_by_id(g.user_id)
        return jsonify({"user": user}), 200
    except Exception as exc:
        logger.exception("Profile fetch failed: %s", exc)
        raise
