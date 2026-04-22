# backend/app/routes/logs.py
"""Habit logging routes."""

from flask import Blueprint, current_app, jsonify, request

from app.utils.decorators import jwt_required
from app.utils.logger import get_logger

bp = Blueprint("logs", __name__, url_prefix="/api/logs")
logger = get_logger(__name__)


def get_log_service():
    return current_app.extensions["log_service"]


@bp.route("", methods=["GET"])
@jwt_required
def list_logs():
    try:
        from flask import g

        filters = {
            "habit_id": request.args.get("habit_id"),
            "date_from": request.args.get("from"),
            "date_to": request.args.get("to"),
        }
        logs = get_log_service().get_logs(g.user_id, filters)
        logger.info("Fetched %s logs for user %s", len(logs), g.user_id)
        return jsonify({"logs": logs}), 200
    except ValueError as exc:
        logger.warning("Log query validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("List logs failed: %s", exc)
        raise


@bp.route("", methods=["POST"])
@jwt_required
def create_log():
    try:
        from flask import g

        payload = request.get_json(force=True, silent=True) or {}
        log = get_log_service().log_habit(
            g.user_id, payload.get("habit_id"), payload.get("note")
        )
        logger.info("Created log %s", log.get("id"))
        return jsonify({"log": log}), 201
    except ValueError as exc:
        logger.warning("Create log validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("Create log failed: %s", exc)
        raise


@bp.route("/<log_id>", methods=["DELETE"])
@jwt_required
def delete_log(log_id):
    try:
        from flask import g

        get_log_service().delete_log(log_id, g.user_id)
        logger.info("Deleted log %s", log_id)
        return jsonify({"success": True}), 200
    except Exception as exc:
        logger.exception("Delete log failed: %s", exc)
        raise


@bp.route("/streak/<habit_id>", methods=["GET"])
@jwt_required
def streak(habit_id):
    try:
        from flask import g

        habit_service = current_app.extensions["habit_service"]
        habit_service.get_habit(habit_id, g.user_id)
        streak_value = get_log_service().get_streak(habit_id)
        logger.info("Streak for habit %s: %s", habit_id, streak_value)
        return jsonify({"habit_id": habit_id, "streak": streak_value}), 200
    except Exception as exc:
        logger.exception("Streak fetch failed: %s", exc)
        raise


@bp.route("/summary", methods=["GET"])
@jwt_required
def summary():
    try:
        from flask import g

        data = get_log_service().get_30_day_summary(g.user_id)
        logger.info("Summary for user %s with %s habits", g.user_id, len(data))
        return jsonify({"summary": data}), 200
    except Exception as exc:
        logger.exception("Summary failed: %s", exc)
        raise
