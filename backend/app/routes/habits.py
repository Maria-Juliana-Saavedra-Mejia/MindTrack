# backend/app/routes/habits.py
"""Habit CRUD routes."""

from flask import Blueprint, current_app, jsonify, request

from app.utils.decorators import jwt_required
from app.utils.logger import get_logger

bp = Blueprint("habits", __name__, url_prefix="/api/habits")
logger = get_logger(__name__)


def get_habit_service():
    return current_app.extensions["habit_service"]


@bp.route("", methods=["GET"])
@jwt_required
def list_habits():
    try:
        from flask import g

        active_only = request.args.get("active_only", "false").lower() == "true"
        habits = get_habit_service().get_habits(g.user_id, active_only=active_only)
        logger.info("Listed habits for user %s", g.user_id)
        return jsonify({"habits": habits}), 200
    except Exception as exc:
        logger.exception("List habits failed: %s", exc)
        raise


@bp.route("", methods=["POST"])
@jwt_required
def create_habit():
    try:
        from flask import g

        payload = request.get_json(force=True, silent=True) or {}
        habit = get_habit_service().create_habit(g.user_id, payload)
        logger.info("Created habit %s", habit.get("id"))
        return jsonify({"habit": habit}), 201
    except ValueError as exc:
        logger.warning("Create habit validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("Create habit failed: %s", exc)
        raise


@bp.route("/<habit_id>", methods=["GET"])
@jwt_required
def get_habit(habit_id):
    try:
        from flask import g

        habit = get_habit_service().get_habit(habit_id, g.user_id)
        logger.info("Fetched habit %s", habit_id)
        return jsonify({"habit": habit}), 200
    except Exception as exc:
        logger.exception("Get habit failed: %s", exc)
        raise


@bp.route("/<habit_id>", methods=["PUT"])
@jwt_required
def update_habit(habit_id):
    try:
        from flask import g

        payload = request.get_json(force=True, silent=True) or {}
        habit = get_habit_service().update_habit(habit_id, g.user_id, payload)
        logger.info("Updated habit %s", habit_id)
        return jsonify({"habit": habit}), 200
    except ValueError as exc:
        logger.warning("Update habit validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("Update habit failed: %s", exc)
        raise


@bp.route("/<habit_id>", methods=["DELETE"])
@jwt_required
def delete_habit(habit_id):
    try:
        from flask import g

        get_habit_service().delete_habit(habit_id, g.user_id)
        logger.info("Deleted habit %s", habit_id)
        return jsonify({"success": True}), 200
    except Exception as exc:
        logger.exception("Delete habit failed: %s", exc)
        raise
