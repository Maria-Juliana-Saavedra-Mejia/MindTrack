# backend/tests/test_utils_and_models.py
"""Tests for utilities and model helpers."""

import jwt
import pytest
from bson import ObjectId
from starlette.testclient import TestClient
from unittest.mock import MagicMock

from app.models.habit import Habit
from app.models.user import User
from app.utils.logger import get_logger

_TEST_JWT_SECRET = "a-very-long-test-secret-key-for-jwt-testing"


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
    return collections


def test_user_invalid_email():
    with pytest.raises(ValueError):
        User(full_name="A", email="bad", password="password123")


def test_user_password_verification():
    user = User(full_name="A", email="a@b.com", password="password123")
    assert user.verify_password("password123") is True
    assert user.verify_password("wrong") is False


def test_user_password_verification_bcrypt_from_dict():
    from app.utils.passwords import hash_password

    h = hash_password("secretpw")
    user = User.from_dict(
        {
            "full_name": "A",
            "email": "a@b.com",
            "password_hash": h,
        }
    )
    assert user.verify_password("secretpw") is True
    assert user.verify_password("wrong") is False


def test_user_legacy_plain_password_from_dict():
    user = User.from_dict(
        {
            "full_name": "A",
            "email": "a@b.com",
            "password": "legacyplain",
        }
    )
    assert user.verify_password("legacyplain") is True


def test_habit_from_dict_roundtrip():
    data = {
        "user_id": None,
        "name": "Run",
        "description": "",
        "frequency": "daily",
        "category": "health",
        "color": "#fff",
        "icon": "🏃",
        "is_active": True,
        "created_at": None,
    }
    habit = Habit.from_dict(data)
    assert habit.is_valid() is True


def test_get_logger_singleton():
    log_a = get_logger("test_logger_module")
    log_b = get_logger("test_logger_module")
    assert log_a is log_b


def test_fastapi_404_returns_json_error_shape(mongo_stub, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", _TEST_JWT_SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from fapi.app import build_app

    with TestClient(build_app()) as client:
        resp = client.get("/missing-route-that-does-not-exist-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("error") is True
    assert "status" in body


def test_fastapi_jwt_protects_api_habits(mongo_stub, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("JWT_SECRET", _TEST_JWT_SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    uid = ObjectId()
    from fapi.app import build_app

    with TestClient(build_app()) as client:
        habits = mongo_stub["habits"]
        chain = MagicMock()
        chain.sort.return_value = []
        habits.find.return_value = chain

        secret = client.app.state.jwt_secret
        token = jwt.encode({"sub": str(uid)}, secret, algorithm="HS256")
        ok = client.get(
            "/api/habits",
            headers={"Authorization": f"Bearer {token}"},
        )
        bad = client.get(
            "/api/habits",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )
    assert ok.status_code == 200
    assert "habits" in ok.json()
    assert bad.status_code == 401
