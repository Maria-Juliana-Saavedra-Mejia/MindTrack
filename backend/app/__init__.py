# backend/app/__init__.py
"""Flask application factory for MindTrack."""

import os

from bson import ObjectId
from flask import Flask, render_template, send_file, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from pymongo import MongoClient

from app.config import Config
from app.routes import ai_bp, auth_bp, habits_bp, logs_bp
from app.services import AIService, AuthService, HabitService, LogService
from app.utils.error_handlers import register_error_handlers
from app.utils.logger import get_logger


class MongoJSONProvider(DefaultJSONProvider):
    """JSON encoder that understands BSON ObjectIds."""

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


def create_app():
    """Build and configure the Flask application."""
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
    flask_cfg = Config.to_flask_config()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    app = Flask(
        __name__,
        template_folder=os.path.join(repo_root, "frontend", "templates"),
        static_folder=os.path.join(repo_root, "frontend", "static"),
    )
    app.config.update(flask_cfg)
    app.json = MongoJSONProvider(app)

    log = get_logger(__name__)
    log.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    client = MongoClient(app.config["MONGO_URI"], **Config.mongo_client_kwargs())
    db = client[app.config["MONGO_DB_NAME"]]

    db["users"].create_index("email", unique=True)
    db["habit_logs"].create_index(
        [("user_id", 1), ("habit_id", 1), ("logged_at", -1)]
    )
    db["habits"].create_index([("user_id", 1), ("is_active", 1)])

    habit_service = HabitService(db)
    log_service = LogService(db, habit_service)
    auth_service = AuthService(
        db,
        jwt_secret=app.config["JWT_SECRET"],
        jwt_expiry_hours=app.config["JWT_EXPIRY_HOURS"],
    )
    ai_service = AIService(db, openai_api_key=app.config["OPENAI_API_KEY"])

    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = db
    app.extensions["auth_service"] = auth_service
    app.extensions["habit_service"] = habit_service
    app.extensions["log_service"] = log_service
    app.extensions["ai_service"] = ai_service

    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(ai_bp)

    def _index_document():
        """Single entry document at repo root (full login/register UI)."""
        return send_from_directory(repo_root, "index.html")

    @app.route("/")
    def home():
        return _index_document()

    @app.get("/index.html")
    def index_html():
        return _index_document()

    @app.route("/login")
    def login_page():
        return _index_document()

    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/habits")
    def habits_page():
        return render_template("habits.html")

    @app.route("/log")
    def log_page():
        return render_template("log.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    _frontend_static = os.path.join(repo_root, "frontend", "static")

    @app.get("/frontend/static/<path:filename>")
    def frontend_static(filename):
        return send_from_directory(_frontend_static, filename)

    @app.get("/favicon.ico")
    def _favicon():
        return send_file(
            os.path.join(_frontend_static, "favicon.svg"),
            mimetype="image/svg+xml",
        )

    # /api/* only; use r"/api/.*" not r"/api/*" (regex * repeats "/", not the rest of the path)
    CORS(
        app,
        resources=Config.flask_cors_api_resources(),
    )

    return app
