# backend/app/routes/ai.py
"""AI insight routes."""

from flask import Blueprint, current_app, jsonify

from app.utils.decorators import jwt_required
from app.utils.logger import get_logger

bp = Blueprint("ai", __name__, url_prefix="/api/ai")
logger = get_logger(__name__)


def get_ai_service():
    return current_app.extensions["ai_service"]


@bp.route("/insights", methods=["GET"])
@jwt_required
def insights():
    try:
        from flask import g

        data = get_ai_service().get_latest_insights(g.user_id)
        logger.info("Fetched AI insights for user %s", g.user_id)
        return jsonify({"insight": data}), 200
    except Exception as exc:
        logger.exception("Fetch insights failed: %s", exc)
        raise


@bp.route("/generate", methods=["POST"])
@jwt_required
def generate():
    try:
        from flask import g

        result = get_ai_service().generate_insights(g.user_id)
        logger.info("Generated AI insight for user %s", g.user_id)
        return jsonify({"insight": result}), 200
    except ValueError as exc:
        logger.warning("AI generate validation error: %s", exc)
        return jsonify({"error": True, "message": str(exc), "status": 400}), 400
    except Exception as exc:
        logger.exception("AI generate failed: %s", exc)
        raise
