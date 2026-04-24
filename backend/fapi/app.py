# fapi/app.py
"""FastAPI application — API + static pages (`python run.py`)."""

import os
import re
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Config
from app.services import AIService, AuthService, HabitService, LogService
from app.utils.logger import get_logger
from fapi.deps import register_bearer_error_handler
from fapi.exception_handlers import register_domain_handlers
from fapi.routers import ai, auth, habits, logs

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_page_log = get_logger(__name__)

_MONGO_SERVER_SELECTION_TIMEOUT_MS = 8000

_INDEX_META_DEV_PORT_RE = re.compile(
    r'(<meta\s+name="mindtrack-dev-api-port"\s+content=")([^"]*)(")',
    re.IGNORECASE,
)


def _effective_listen_port(request: Request) -> int:
    """Same resolution order as /mindtrack-http-port (int for HTML injection)."""
    u = request.url
    default_port = 443 if str(u.scheme).lower() == "https" else 80
    if u.port is not None and u.port != default_port:
        return int(u.port)
    raw = os.environ.get("MINDTRACK_HTTP_PORT", "").strip()
    if raw.isdigit():
        return int(raw)
    host_hdr = (request.headers.get("host") or "").strip()
    if ":" in host_hdr:
        tail = host_hdr.rsplit(":", 1)[-1]
        if tail.isdigit():
            return int(tail)
    return 5050


def _index_html_response(request: Request) -> HTMLResponse:
    """
    Serve index.html with mindtrack-dev-api-port filled from this request.

    Ensures Live-Server-style flows that read the meta see the real listen port when
    the page is opened via run.py (avoids stale empty meta + wrong default 5050).
    """
    path = os.path.join(_REPO_ROOT, "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    port = _effective_listen_port(request)

    def _repl(m):
        return f"{m.group(1)}{port}{m.group(3)}"

    html_new, n = _INDEX_META_DEV_PORT_RE.subn(_repl, html, count=1)
    if n == 0:
        html_new = html
    return HTMLResponse(content=html_new)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
    Config.validate()
    cfg = Config.to_app_config()
    log = get_logger(__name__)
    client = None
    try:
        client = MongoClient(
            cfg["MONGO_URI"],
            serverSelectionTimeoutMS=_MONGO_SERVER_SELECTION_TIMEOUT_MS,
            **Config.mongo_client_kwargs(),
        )
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
        log.info(
            "MindTrack API ready (pid=%s) — file logs also written to logs/mindtrack.log "
            "(project root, next to run.py).",
            os.getpid(),
        )
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        if client is not None:
            client.close()
        msg_l = str(exc).lower()
        tls_hint = ""
        if any(
            s in msg_l
            for s in ("certificate", "cert_verify", "ssl", "tls", "issuer")
        ):
            tls_hint = (
                " TLS/certificate error: on macOS with python.org Python, open "
                "Applications/Python 3.x and run “Install Certificates.command”. "
                "MindTrack passes certifi’s CA bundle by default; ensure "
                "`pip install -r requirements.txt` includes certifi. Dev-only "
                "workaround: MONGO_TLS_INSECURE=1 in .env (never in production)."
            )
        raise RuntimeError(
            "Cannot connect to MongoDB within "
            f"{_MONGO_SERVER_SELECTION_TIMEOUT_MS // 1000}s. "
            "Check MONGO_URI and MONGO_DB_NAME in .env (project root, next to run.py). "
            "Start Mongo locally, use MongoDB Atlas, or run: docker compose up -d."
            + tls_hint
        ) from exc
    try:
        yield
    finally:
        if client is not None:
            client.close()


def build_app() -> FastAPI:
    app = FastAPI(title="MindTrack", lifespan=lifespan)
    _cors_opts = Config.fastapi_cors_middleware_options()
    if not _cors_opts.get("allow_origins"):
        _page_log.warning(
            "CORS allow_origins is empty (usually FLASK_ENV/ENV=production without CORS_ORIGINS). "
            "The browser will block requests from Live Server (e.g. :5500) and GitHub Pages. "
            "Set CORS_ORIGINS to a comma-separated list of UI origins, or use "
            "FLASK_ENV=development for local API-only work."
        )
    app.add_middleware(CORSMiddleware, **_cors_opts)

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

    def _safe_template_response(request: Request, template_name: str):
        try:
            return _templates.TemplateResponse(
                request,
                template_name,
                {"mindtrack_http_port": _effective_listen_port(request)},
            )
        except Exception as exc:
            _page_log.exception("Template render failed: %s", template_name)
            if Config._runtime_env_name() != "production":
                body = (
                    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
                    "<title>MindTrack</title></head><body>"
                    "<h1>Page failed to render</h1>"
                    f"<p>Template: <code>{escape(template_name)}</code></p>"
                    f"<pre style=\"white-space:pre-wrap\">{escape(str(exc))}</pre>"
                    "</body></html>"
                )
                return HTMLResponse(content=body, status_code=500)
            return HTMLResponse(
                "<!DOCTYPE html><html><body><p>Page unavailable.</p></body></html>",
                status_code=500,
            )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/mindtrack-http-port")
    def mindtrack_http_port(request: Request):
        """
        Plain-text listen port for local dev (Live Server + api.js cross-port probe).

        Prefer the port from this HTTP request URL — survives uvicorn --reload subprocesses
        where MINDTRACK_HTTP_PORT may not match the worker.
        """
        u = request.url
        default_port = 443 if str(u.scheme).lower() == "https" else 80
        if u.port is not None and u.port != default_port:
            return PlainTextResponse(str(u.port))
        raw = os.environ.get("MINDTRACK_HTTP_PORT", "").strip()
        if raw.isdigit():
            return PlainTextResponse(raw)
        host_hdr = (request.headers.get("host") or "").strip()
        if ":" in host_hdr:
            tail = host_hdr.rsplit(":", 1)[-1]
            if tail.isdigit():
                return PlainTextResponse(tail)
        return PlainTextResponse("5050")

    @app.get("/")
    def home(request: Request):
        return _index_html_response(request)

    @app.get("/index.html")
    def index_html(request: Request):
        return _index_html_response(request)

    @app.get("/login")
    def login_page(request: Request):
        return _index_html_response(request)

    @app.get("/dashboard")
    def dashboard_page(request: Request):
        return _safe_template_response(request, "dashboard.html")

    @app.get("/habits")
    def habits_page(request: Request):
        return _safe_template_response(request, "habits.html")

    @app.get("/log")
    def log_page(request: Request):
        return _safe_template_response(request, "log.html")

    @app.get("/profile")
    def profile_page(request: Request):
        return _safe_template_response(request, "profile.html")

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
    # Same files as `/static` mount (see test_static_login_css)
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
    return app
