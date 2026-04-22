# fapi/app.py
"""FastAPI application — API + static pages (replaces Flask for `python run.py`)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import Config
from app.services import AIService, AuthService, HabitService, LogService
from fapi.deps import register_bearer_error_handler
from fapi.exception_handlers import register_domain_handlers
from fapi.routers import ai, auth, habits, logs

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class _ApiPreflightCorsMiddleware(BaseHTTPMiddleware):
    """
    Outermost HTTP layer: handle OPTIONS for /api/* with explicit CORS so browser
    preflights always see Access-Control-Allow-Origin (belt-and-suspenders with
    CORSMiddleware and odd Starlette/Starlette+proxy edge cases).
    """

    _ACAM = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api") and request.method == "OPTIONS":
            arh = request.headers.get("access-control-request-headers", "")
            hdrs = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": self._ACAM,
                "Access-Control-Max-Age": "600",
            }
            hdrs["Access-Control-Allow-Headers"] = (
                arh
                or "content-type, authorization, x-requested-with"
            )
            return Response(status_code=204, content=b"", headers=hdrs)
        response = await call_next(request)
        if path.startswith("/api") and not response.headers.get(
            "access-control-allow-origin"
        ):
            response.headers["Access-Control-Allow-Origin"] = "*"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
    Config.validate()
    cfg = Config.to_flask_config()
    client = MongoClient(cfg["MONGO_URI"])
    db = client[cfg["MONGO_DB_NAME"]]
    db["users"].create_index("email", unique=True)
    db["habit_logs"].create_index(
        [("user_id", 1), ("habit_id", 1), ("logged_at", -1)]
    )
    db["habits"].create_index([("user_id", 1), ("is_active", 1)])
    habit_service = HabitService(db)
    log_service = LogService(db, habit_service)
    auth_service = AuthService(
        db,
        jwt_secret=cfg["JWT_SECRET"],
        jwt_expiry_hours=cfg["JWT_EXPIRY_HOURS"],
    )
    ai_service = AIService(db, openai_api_key=cfg["OPENAI_API_KEY"])
    app.state.mongo_client = client
    app.state.db = db
    app.state.jwt_secret = cfg["JWT_SECRET"]
    app.state.habit_service = habit_service
    app.state.log_service = log_service
    app.state.auth_service = auth_service
    app.state.ai_service = ai_service
    try:
        yield
    finally:
        client.close()


def build_app() -> FastAPI:
    app = FastAPI(title="MindTrack", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, **Config.fastapi_cors_middleware_options())
    register_bearer_error_handler(app)
    register_domain_handlers(app)

    @app.exception_handler(StarletteHTTPException)
    def http_exception(_: Request, exc: StarletteHTTPException):
        msg = exc.detail if isinstance(exc.detail, str) else "Error"
        return JSONResponse(
            content={"error": True, "message": msg, "status": exc.status_code},
            status_code=exc.status_code,
        )

    _templates = Jinja2Templates(
        directory=os.path.join(_REPO_ROOT, "frontend", "templates")
    )
    _front = os.path.join(_REPO_ROOT, "frontend", "static")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def home():
        return FileResponse(os.path.join(_REPO_ROOT, "index.html"))

    @app.get("/index.html")
    def index_html():
        return FileResponse(os.path.join(_REPO_ROOT, "index.html"))

    @app.get("/login")
    def login_page():
        return FileResponse(os.path.join(_REPO_ROOT, "index.html"))

    @app.get("/dashboard")
    def dashboard_page(request: Request):
        return _templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/habits")
    def habits_page(request: Request):
        return _templates.TemplateResponse("habits.html", {"request": request})

    @app.get("/log")
    def log_page(request: Request):
        return _templates.TemplateResponse("log.html", {"request": request})

    @app.get("/favicon.ico")
    def favicon():
        return FileResponse(
            os.path.join(_front, "favicon.svg"),
            media_type="image/svg+xml",
        )

    app.mount(
        "/frontend/static",
        StaticFiles(directory=_front),
        name="frontstatic",
    )
    # Same files as legacy Flask `static_url_path` (see test_static_login_css)
    app.mount(
        "/static",
        StaticFiles(directory=_front),
        name="static",
    )

    app.include_router(auth.router)
    app.include_router(habits.router)
    # Register /summary and /streak before /{log_id} patterns for clarity
    app.include_router(logs.router)
    app.include_router(ai.router)
    # Added last so it runs first (outermost) and can answer OPTIONS for /api before routing.
    app.add_middleware(_ApiPreflightCorsMiddleware)
    return app
