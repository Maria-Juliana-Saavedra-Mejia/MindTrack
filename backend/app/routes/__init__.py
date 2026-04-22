# app/routes/__init__.py
"""HTTP route blueprints."""

from app.routes.auth import bp as auth_bp
from app.routes.habits import bp as habits_bp
from app.routes.logs import bp as logs_bp
from app.routes.ai import bp as ai_bp

__all__ = ["auth_bp", "habits_bp", "logs_bp", "ai_bp"]
