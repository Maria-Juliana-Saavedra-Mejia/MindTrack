# backend/tests/test_mongo_integration.py
"""Real MongoDB round-trip tests (opt-in via RUN_MONGO_INTEGRATION=1)."""

from __future__ import annotations

import os
import uuid

import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import Config
from app.services import AuthService, HabitService, LogService

_SKIP_MONGO_HELP = (
    "Cannot connect to MongoDB with the current MONGO_URI. "
    "Start Mongo locally (e.g. `docker compose up -d` for mongodb://localhost:27017) "
    "or set MONGO_URI in .env to your cluster (MongoDB Atlas). "
    "Inspect collections with MongoDB Compass using the same URI and MONGO_DB_NAME."
)

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUN_MONGO_INTEGRATION") != "1",
        reason="set RUN_MONGO_INTEGRATION=1 to run real MongoDB integration tests",
    ),
    pytest.mark.skipif(
        not os.environ.get("MONGO_URI", "").strip(),
        reason="MONGO_URI must be set (e.g. in .env) for integration tests",
    ),
]


@pytest.fixture(scope="module")
def mongo_bundle():
    saved_name = os.environ.get("MONGO_DB_NAME")
    db_name = f"mindtrack_int_{uuid.uuid4().hex[:12]}"
    os.environ["MONGO_DB_NAME"] = db_name
    Config.validate()
    cfg = Config.to_flask_config()
    client = MongoClient(
        cfg["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        **Config.mongo_client_kwargs(),
    )
    try:
        client.admin.command("ping")
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        client.close()
        pytest.skip(f"{_SKIP_MONGO_HELP} ({exc})")

    db = client[db_name]
    try:
        db["users"].create_index("email", unique=True)
        db["habit_logs"].create_index(
            [("user_id", 1), ("habit_id", 1), ("logged_at", -1)]
        )
        db["habits"].create_index([("user_id", 1), ("is_active", 1)])
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        client.close()
        pytest.skip(f"{_SKIP_MONGO_HELP} ({exc})")
    habit_service = HabitService(db)
    log_service = LogService(db, habit_service)
    auth_service = AuthService(
        db,
        jwt_secret=cfg["JWT_SECRET"],
        jwt_expiry_hours=cfg["JWT_EXPIRY_HOURS"],
    )
    bundle = {
        "client": client,
        "db": db,
        "auth": auth_service,
        "habit": habit_service,
        "log": log_service,
        "db_name": db_name,
    }
    try:
        yield bundle
    finally:
        try:
            client.drop_database(db_name)
        finally:
            client.close()
        if saved_name is None:
            os.environ.pop("MONGO_DB_NAME", None)
        else:
            os.environ["MONGO_DB_NAME"] = saved_name


def test_password_stored_and_read_as_plain_text(mongo_bundle):
    """Password field in Mongo matches submitted string (no hashing)."""
    auth = mongo_bundle["auth"]
    db = mongo_bundle["db"]
    plain = "student_plain_pw_123"
    email = f"p_{uuid.uuid4().hex[:10]}@example.com"
    auth.register_user(
        {"full_name": "Integration User", "email": email, "password": plain}
    )
    doc = db["users"].find_one({"email": email})
    assert doc is not None
    assert doc.get("password") == plain


def test_login_last_login_token_and_habit_log_roundtrip(mongo_bundle):
    auth = mongo_bundle["auth"]
    habit_svc = mongo_bundle["habit"]
    log_svc = mongo_bundle["log"]
    db = mongo_bundle["db"]
    email = f"h_{uuid.uuid4().hex[:10]}@example.com"
    password = "same_pw_roundtrip"
    auth.register_user(
        {"full_name": "Habit User", "email": email, "password": password}
    )
    before = db["users"].find_one({"email": email})
    assert before.get("last_login") is None

    out = auth.login_user(email, password)
    assert out.get("access_token")
    assert out["user"]["email"] == email

    after = db["users"].find_one({"email": email})
    assert after.get("last_login") is not None

    uid = out["user"]["id"]
    habit = habit_svc.create_habit(
        uid,
        {
            "name": "Morning run",
            "description": "",
            "frequency": "daily",
            "category": "health",
            "color": "#0F6E56",
            "icon": "🏃",
            "is_active": True,
        },
    )
    hid = habit["id"]
    log_svc.log_habit(uid, hid, note="completed")
    logs = log_svc.get_logs(uid, {})
    assert len(logs) >= 1
    assert logs[0]["habit_id"] == hid
