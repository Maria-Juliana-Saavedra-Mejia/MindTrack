# backend/tests/test_api_integration.py
"""Integration tests (FastAPI + Uvicorn stack) with Mongo mocked."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from bson import ObjectId
from starlette.testclient import TestClient

from app.utils.error_handlers import InvalidCredentialsError

from tests.conftest import FakeCursor


@pytest.fixture
def mongo_stub(monkeypatch):
    collections = {}

    def get_collection(name):
        if name not in collections:
            coll = MagicMock()
            coll.find_one.return_value = None
            coll.find.return_value = []
            collections[name] = coll
        return collections[name]

    db = MagicMock()
    db.__getitem__.side_effect = get_collection
    mongo_client = MagicMock()
    mongo_client.__getitem__.return_value = db
    import fapi.app as fapi_mod

    monkeypatch.setattr(fapi_mod, "MongoClient", lambda *a, **k: mongo_client)
    # Eager-create collections tests index as mongo_stub["habits"] (before any TestClient).
    for _name in ("users", "habits", "habit_logs", "ai_insights"):
        get_collection(_name)
    return collections


@pytest.fixture
def client(mongo_stub, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from fapi.app import build_app

    with TestClient(build_app()) as c:
        yield c


def _token(client, user_id):
    secret = client.app.state.jwt_secret
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_mindtrack_http_port_cors_allows_live_server_with_strict_cors_origins(
    mongo_stub, monkeypatch,
):
    """
    When CORS_ORIGINS is an explicit whitelist, api.js discovery from Live Server (:5500)
    must still read GET /mindtrack-http-port — non-production adds a loopback origin regex.
    """
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://production.example.com,http://127.0.0.1:5500",
    )
    monkeypatch.setenv("FLASK_ENV", "development")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5050") as c:
        r = c.get(
            "/mindtrack-http-port",
            headers={"Origin": "http://127.0.0.1:5500"},
        )
    assert r.status_code == 200
    acao = r.headers.get("access-control-allow-origin")
    assert acao in ("http://127.0.0.1:5500", "*"), acao


def test_mindtrack_http_port_prefers_request_url_port(mongo_stub, monkeypatch):
    """Echoes the port used in the HTTP request URL (reload-safe vs env-only)."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MINDTRACK_HTTP_PORT", "9999")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5066") as c:
        r = c.get("/mindtrack-http-port")
    assert r.status_code == 200
    assert r.text.strip() == "5066"


def test_index_html_injects_dev_api_port_meta_from_request_url(mongo_stub, monkeypatch):
    """Served login index fills mindtrack-dev-api-port so api.js matches run.py listen port."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MINDTRACK_HTTP_PORT", "9999")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5077") as c:
        r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert 'content="5077"' in body
    assert 'name="mindtrack-dev-api-port"' in body


def test_dashboard_template_injects_dev_api_port_meta(mongo_stub, monkeypatch):
    """Jinja base.html exposes listen port so api.js matches run.py when UI is on /dashboard."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5099") as c:
        r = c.get("/dashboard")
    assert r.status_code == 200
    assert 'name="mindtrack-dev-api-port"' in r.text
    assert 'content="5099"' in r.text


def test_favicon_reachable(client):
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("image/svg")


def test_api_cors_preflight_includes_allow_origin(client):
    """Browser preflight (OPTIONS) gets CORS allow-origin for /api/* ."""
    resp = client.options(
        "/api/auth/register",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, authorization",
        },
    )
    assert resp.status_code in (200, 204, 400, 405)
    acao = resp.headers.get("access-control-allow-origin")
    assert acao in ("http://127.0.0.1:5500", "*")


def test_cors_merges_live_server_when_cors_origins_github_only_in_development(
    mongo_stub, monkeypatch,
):
    """CORS_ORIGINS may list only GitHub Pages; local Live Server must still work in dev."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CORS_ORIGINS", "https://user.github.io")
    monkeypatch.setenv("FLASK_ENV", "development")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5050") as c:
        r = c.options(
            "/api/auth/register",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization",
            },
        )
    assert r.status_code in (200, 204, 400, 405)
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"


def test_cors_does_not_merge_live_server_in_production(mongo_stub, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CORS_ORIGINS", "https://user.github.io")
    monkeypatch.setenv("FLASK_ENV", "production")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5050") as c:
        r = c.options(
            "/api/auth/register",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization",
            },
        )
    assert r.status_code in (200, 204, 400, 405)
    assert r.headers.get("access-control-allow-origin") in (None, "")


def test_cors_merges_live_server_when_merge_flag_in_production(mongo_stub, monkeypatch):
    """Production + explicit CORS_ORIGINS can still allow Live Server when opt-in flag is set."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CORS_ORIGINS", "https://user.github.io")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("MINDTRACK_MERGE_LIVE_SERVER_CORS", "1")
    from fapi.app import build_app

    with TestClient(build_app(), base_url="http://127.0.0.1:5050") as c:
        r = c.options(
            "/api/auth/register",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization",
            },
        )
    assert r.status_code in (200, 204, 400, 405)
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"


def test_api_cors_preflight_allows_localhost_live_server(client):
    """Live Server often uses http://localhost:5500 (not 127.0.0.1)."""
    resp = client.options(
        "/api/auth/register",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, authorization",
        },
    )
    assert resp.status_code in (200, 204, 400, 405)
    acao = resp.headers.get("access-control-allow-origin")
    assert acao in ("http://localhost:5500", "*")


def test_static_login_css_and_logo_reachable(client):
    for path in ("/static/css/login.css", "/static/images/mindtrack-logo.png"):
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_frontend_static_login_assets_reachable(client):
    for path in (
        "/frontend/static/css/login.css",
        "/frontend/static/images/mindtrack-logo.png",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_entry_routes_serve_same_root_index_html(client):
    for path in ("/", "/login", "/index.html"):
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.content
        assert b'id="login-form"' in data
        assert b"frontend/static/js/auth.js" in data
        assert b"frontend/static/css/login.css" in data
        assert b"frontend/static/images/mindtrack-logo.png" in data


def test_dashboard_template_renders(client):
    """Templates use Flask-style url_for('static', ...); FastAPI injects a compatible helper."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b'id="kpi-active"' in resp.content
    assert b"/static/js/dashboard.js" in resp.content


def test_profile_page_renders(client):
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"/static/js/profile.js" in resp.content
    assert b"/static/css/profile.css" in resp.content
    assert b'href="/profile"' in resp.content


def test_login_invalid_credentials(client, mongo_stub):
    users = mongo_stub["users"]
    users.find_one.return_value = None
    resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] is True


def test_habits_requires_auth(client):
    resp = client.get("/api/habits")
    assert resp.status_code == 401


def test_register_password_too_short_returns_422(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "A",
            "email": "shortpw@example.com",
            "password": "short",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") is True
    assert body.get("status") == 422
    assert "details" in body


def test_register_duplicate(client, mongo_stub):
    users = mongo_stub["users"]
    users.find_one.return_value = {"email": "dup@example.com"}
    resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "Dup",
            "email": "dup@example.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 409


def test_register_auto_login_fails_returns_503(client, mongo_stub, monkeypatch):
    """After successful insert, auto-login failure must not use HTTP 500."""
    users = mongo_stub["users"]
    oid = ObjectId()
    users.find_one.side_effect = [
        None,
        {
            "_id": oid,
            "full_name": "New User",
            "email": "new503@example.com",
            "password": "password123",
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "preferences": {},
        },
    ]
    users.insert_one.return_value = MagicMock(inserted_id=oid)

    auth = client.app.state.auth_service

    def fail_login(*_a, **_kw):
        raise InvalidCredentialsError("simulated auto-login failure")

    monkeypatch.setattr(auth, "login_user", fail_login)

    resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "New User",
            "email": "new503@example.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] is True
    assert body["status"] == 503
    assert (
        "sign-in" in body["message"].lower()
        or "login" in body["message"].lower()
    )


def test_logout(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_profile(client, mongo_stub):
    uid = ObjectId()
    users = mongo_stub["users"]
    users.find_one.return_value = {
        "_id": uid,
        "full_name": "Tester",
        "email": "t@example.com",
        "preferences": {},
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
    token = _token(client, uid)
    resp = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "t@example.com"


def test_list_habits_authenticated(client, mongo_stub):
    uid = ObjectId()
    habits = mongo_stub["habits"]
    chain = MagicMock()
    chain.sort.return_value = []
    habits.find.return_value = chain
    token = _token(client, uid)
    resp = client.get(
        "/api/habits", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["habits"] == []


def test_logs_summary_authenticated(client, mongo_stub):
    uid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = []
    token = _token(client, uid)
    resp = client.get(
        "/api/logs/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


def test_create_habit_validation_error(client, mongo_stub):
    uid = ObjectId()
    token = _token(client, uid)
    resp = client.post(
        "/api/habits",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Bad", "frequency": "invalid", "category": "health"},
    )
    assert resp.status_code == 400


def test_ai_generate_validation(client, mongo_stub):
    uid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = []
    token = _token(client, uid)
    resp = client.post(
        "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400


def test_ai_generate_missing_openai_key_returns_503(mongo_stub, monkeypatch):
    """When provider is openai and OPENAI_API_KEY is unset, return 503."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("MINDTRACK_INSIGHT_PROVIDER", "openai")
    from fapi.app import build_app

    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = [
        {
            "_id": hid,
            "user_id": uid,
            "name": "Run",
            "category": "health",
            "is_active": True,
        }
    ]
    logs = mongo_stub["habit_logs"]
    logs.count_documents.return_value = 5
    logs.find.return_value = FakeCursor([])
    with TestClient(build_app()) as client:
        token = _token(client, uid)
        resp = client.post(
            "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 503
    body = resp.json()
    assert body.get("error") is True
    assert "OPENAI_API_KEY" in body["message"]
    assert "not set" in body["message"].lower() or "not configured" in body["message"].lower()


def test_ai_generate_auto_without_key_returns_template(mongo_stub, monkeypatch):
    """Default auto + no key uses template insights (200, no OpenAI)."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("MINDTRACK_INSIGHT_PROVIDER", raising=False)
    from fapi.app import build_app

    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = [
        {
            "_id": hid,
            "user_id": uid,
            "name": "Run",
            "category": "health",
            "is_active": True,
        }
    ]
    logs = mongo_stub["habit_logs"]
    logs.count_documents.return_value = 5
    logs.find.return_value = FakeCursor([])
    with TestClient(build_app()) as client:
        token = _token(client, uid)
        resp = client.post(
            "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "insight" in data
    assert data["insight"]["insight_type"] == "template"
    assert data["insight"]["compliment"]
    assert data["insight"]["observation"]
    assert data["insight"]["tip"]


def test_ai_generate_local_skips_openai(monkeypatch, mongo_stub):
    """MINDTRACK_INSIGHT_PROVIDER=local never calls OpenAI even if a key is set."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MINDTRACK_INSIGHT_PROVIDER", "local")
    from fapi.app import build_app

    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = [
        {
            "_id": hid,
            "user_id": uid,
            "name": "Walk",
            "category": "health",
            "is_active": True,
        }
    ]
    logs = mongo_stub["habit_logs"]
    logs.count_documents.return_value = 12
    logs.find.return_value = FakeCursor([])
    with TestClient(build_app()) as client:

        def boom(*_a, **_kw):
            raise AssertionError("OpenAI should not be called in local insight mode")

        monkeypatch.setattr(
            client.app.state.ai_service._client.chat.completions,
            "create",
            boom,
        )
        token = _token(client, uid)
        resp = client.post(
            "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["insight"]["insight_type"] == "template"


def test_ai_generate_openai_error_returns_502(client, mongo_stub, monkeypatch):
    from openai import AuthenticationError

    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = [
        {
            "_id": hid,
            "user_id": uid,
            "name": "Run",
            "category": "health",
            "is_active": True,
        }
    ]
    logs = mongo_stub["habit_logs"]
    logs.count_documents.return_value = 5
    logs.find.return_value = FakeCursor([])
    token = _token(client, uid)

    def boom(*_a, **_kw):
        raise AuthenticationError("bad", response=MagicMock(), body=None)

    monkeypatch.setattr(
        client.app.state.ai_service._client.chat.completions,
        "create",
        boom,
    )
    resp = client.post(
        "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 502
    body = resp.json()
    assert body.get("error") is True
    assert "message" in body
    assert "OPENAI_API_KEY" in body["message"]


def test_ai_generate_openai_rate_limit_falls_back_to_template(client, mongo_stub, monkeypatch):
    """When OpenAI returns rate limit, API serves prepared template insight (200)."""
    from openai import RateLimitError

    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = [
        {
            "_id": hid,
            "user_id": uid,
            "name": "Run",
            "category": "health",
            "is_active": True,
        }
    ]
    logs = mongo_stub["habit_logs"]
    logs.count_documents.return_value = 5
    logs.find.return_value = FakeCursor([])
    token = _token(client, uid)

    def boom(*_a, **_kw):
        raise RateLimitError("rate", response=MagicMock(), body=None)

    monkeypatch.setattr(
        client.app.state.ai_service._client.chat.completions,
        "create",
        boom,
    )
    resp = client.post(
        "/api/ai/generate", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["insight"]["insight_type"] == "template"
    assert data["insight"]["compliment"]
    assert data["insight"]["observation"]
    assert data["insight"]["tip"]


def test_create_log(client, mongo_stub):
    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find_one.return_value = {
        "_id": hid,
        "user_id": uid,
        "name": "Run",
        "description": "",
        "frequency": "daily",
        "category": "health",
        "color": "#fff",
        "icon": "🏃",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    logs = mongo_stub["habit_logs"]
    inserted = ObjectId()
    logs.insert_one.return_value = MagicMock(inserted_id=inserted)
    now = datetime.now(timezone.utc)
    logs.find.return_value = FakeCursor(
        [
            {"logged_at": now},
            {"logged_at": now - timedelta(days=1)},
        ]
    )
    logs.find_one.return_value = {
        "_id": inserted,
        "habit_id": hid,
        "user_id": uid,
        "logged_at": now,
        "note": "",
        "streak_count": 2,
    }
    token = _token(client, uid)
    resp = client.post(
        "/api/logs",
        headers={"Authorization": f"Bearer {token}"},
        json={"habit_id": str(hid), "note": ""},
    )
    assert resp.status_code == 201


def test_create_log_seeds_starter_insight_on_first_checkin(client, mongo_stub):
    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find_one.return_value = {
        "_id": hid,
        "user_id": uid,
        "name": "Read",
        "description": "",
        "frequency": "daily",
        "category": "productivity",
        "color": "#fff",
        "icon": "📚",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    logs = mongo_stub["habit_logs"]
    inserted = ObjectId()
    logs.insert_one.return_value = MagicMock(inserted_id=inserted)
    now = datetime.now(timezone.utc)
    logs.find.return_value = FakeCursor([{"logged_at": now}])
    logs.find_one.return_value = {
        "_id": inserted,
        "habit_id": hid,
        "user_id": uid,
        "logged_at": now,
        "note": "",
        "streak_count": 1,
    }
    logs.count_documents.return_value = 1
    insights = mongo_stub["ai_insights"]
    insights.find_one.return_value = None
    token = _token(client, uid)
    resp = client.post(
        "/api/logs",
        headers={"Authorization": f"Bearer {token}"},
        json={"habit_id": str(hid), "note": ""},
    )
    assert resp.status_code == 201
    insights.insert_one.assert_called_once()
    starter = insights.insert_one.call_args[0][0]
    assert starter.get("insight_type") == "starter"
    assert "Read" in starter.get("compliment", "")


def test_logs_list(client, mongo_stub):
    uid = ObjectId()
    logs = mongo_stub["habit_logs"]
    logs.find.return_value = FakeCursor([])
    token = _token(client, uid)
    resp = client.get(
        "/api/logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


def test_logs_streak(client, mongo_stub):
    uid = ObjectId()
    hid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find_one.return_value = {
        "_id": hid,
        "user_id": uid,
        "name": "Run",
        "description": "",
        "frequency": "daily",
        "category": "health",
        "color": "#fff",
        "icon": "🏃",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    logs = mongo_stub["habit_logs"]
    logs.find.return_value = FakeCursor([])
    token = _token(client, uid)
    resp = client.get(
        f"/api/logs/streak/{hid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
