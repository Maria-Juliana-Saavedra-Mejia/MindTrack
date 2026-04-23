# backend/tests/conftest.py
"""Shared pytest fixtures."""

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

# Repo-root .env loads before defaults so pytest matches `python run.py` for Mongo settings.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "mindtrack_test")
os.environ.setdefault("JWT_SECRET", "a-very-long-test-secret-key-for-jwt-testing")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_EXPIRY_HOURS", "24")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("LOG_LEVEL", "INFO")


@pytest.fixture
def mock_db():
    """Provide a Mongo-like database mock with independent collections."""
    collections = {}

    def get_collection(name):
        if name not in collections:
            collections[name] = MagicMock()
        return collections[name]

    db = MagicMock()
    db.__getitem__.side_effect = get_collection
    return db


@pytest.fixture
def auth_service(mock_db):
    from app.services.auth_service import AuthService

    return AuthService(mock_db, jwt_secret="secret", jwt_expiry_hours=24)


@pytest.fixture
def habit_service(mock_db):
    from app.services.habit_service import HabitService

    return HabitService(mock_db)


@pytest.fixture
def log_service(mock_db, habit_service):
    from app.services.log_service import LogService

    return LogService(mock_db, habit_service)


@pytest.fixture
def sample_user_dict():
    return {
        "_id": ObjectId(),
        "full_name": "Test User",
        "email": "user@example.com",
        "password": "goodpassword",
        "preferences": {"reminder_time": "09:00", "theme": "light"},
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }


@pytest.fixture
def sample_habit_dict(sample_user_dict):
    return {
        "_id": ObjectId(),
        "user_id": sample_user_dict["_id"],
        "name": "Read",
        "description": "Read daily",
        "frequency": "daily",
        "category": "productivity",
        "color": "#0F6E56",
        "icon": "📚",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }


class FakeCursor(list):
    """Minimal cursor supporting .sort chaining."""

    def sort(self, *args, **kwargs):
        return self


@pytest.fixture
def fixed_now():
    return datetime(2024, 1, 10, 12, 0, tzinfo=timezone.utc)
