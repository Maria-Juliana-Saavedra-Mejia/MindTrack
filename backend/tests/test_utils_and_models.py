# backend/tests/test_utils_and_models.py
"""Tests for utilities and model helpers."""

import jwt
import pytest
from flask import Flask

from app.models.habit import Habit
from app.models.user import User
from app.utils.decorators import jwt_required
from app.utils.error_handlers import register_error_handlers
from app.utils.logger import get_logger


def test_user_invalid_email():
    with pytest.raises(ValueError):
        User(full_name="A", email="bad", password="password123")


def test_user_password_verification():
    user = User(full_name="A", email="a@b.com", password="password123")
    assert user.verify_password("password123") is True
    assert user.verify_password("wrong") is False


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


def test_jwt_required_decorator():
    app = Flask(__name__)
    app.config["JWT_SECRET"] = "a-very-long-test-secret-key-for-jwt-testing"

    @app.route("/protected")
    @jwt_required
    def protected():
        from flask import g

        return {"user": g.user_id}

    token = jwt.encode(
        {"sub": "user123"},
        "a-very-long-test-secret-key-for-jwt-testing",
        algorithm="HS256",
    )
    with app.test_client() as client:
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.get_json()["user"] == "user123"
        bad = client.get(
            "/protected",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )
        assert bad.status_code == 401


def test_error_handlers_return_json():
    app = Flask(__name__)
    register_error_handlers(app)
    with app.test_client() as client:
        resp = client.get("/missing-route-that-does-not-exist-xyz")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"] is True
        assert "status" in body
