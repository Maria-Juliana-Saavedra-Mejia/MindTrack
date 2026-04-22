# backend/tests/test_flask_integration.py
"""Lightweight Flask integration tests with Mongo mocked."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from bson import ObjectId

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
    import app as app_package

    monkeypatch.setattr(app_package, "MongoClient", lambda *a, **k: mongo_client)
    return collections


@pytest.fixture
def client(mongo_stub, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from app import create_app

    app = create_app()
    app.testing = True
    return app.test_client()


def _token(client, user_id):
    secret = client.application.config["JWT_SECRET"]
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_api_cors_preflight_includes_allow_origin(client):
    """Browser preflight (OPTIONS) must match /api/.* so CORS headers are set."""
    resp = client.open(
        "/api/auth/register",
        method="OPTIONS",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, authorization",
        },
    )
    assert resp.status_code in (200, 204)
    acao = resp.headers.get("Access-Control-Allow-Origin")
    # CORS(app) defaults allow the request origin or * for all origins
    assert acao in ("http://127.0.0.1:5500", "*")


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
        assert b'id="login-form"' in resp.data
        assert b"frontend/static/js/auth.js" in resp.data
        assert b"frontend/static/css/login.css" in resp.data
        assert b"frontend/static/images/mindtrack-logo.png" in resp.data


def test_login_invalid_credentials(client, mongo_stub):
    users = mongo_stub["users"]
    users.find_one.return_value = None
    resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["error"] is True


def test_habits_requires_auth(client):
    resp = client.get("/api/habits")
    assert resp.status_code == 401


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


def test_logout(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


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
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "t@example.com"


def test_list_habits_authenticated(client, mongo_stub):
    uid = ObjectId()
    habits = mongo_stub["habits"]
    chain = MagicMock()
    chain.sort.return_value = []
    habits.find.return_value = chain
    token = _token(client, uid)
    resp = client.get("/api/habits", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["habits"] == []


def test_logs_summary_authenticated(client, mongo_stub):
    uid = ObjectId()
    habits = mongo_stub["habits"]
    habits.find.return_value = []
    token = _token(client, uid)
    resp = client.get("/api/logs/summary", headers={"Authorization": f"Bearer {token}"})
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
    resp = client.post("/api/ai/generate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


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


def test_logs_list(client, mongo_stub):
    uid = ObjectId()
    logs = mongo_stub["habit_logs"]
    logs.find.return_value = FakeCursor([])
    token = _token(client, uid)
    resp = client.get("/api/logs", headers={"Authorization": f"Bearer {token}"})
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
