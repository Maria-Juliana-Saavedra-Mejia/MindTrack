# backend/tests/test_log_service.py
"""Tests for LogService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from bson import ObjectId

from tests.conftest import FakeCursor


def test_log_habit_creates_document(log_service, mock_db, sample_user_dict, sample_habit_dict):
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    habits.find_one.return_value = sample_habit_dict
    inserted_id = ObjectId()
    logs.insert_one.return_value = MagicMock(inserted_id=inserted_id)
    now = datetime.now(timezone.utc)
    streak_logs = FakeCursor(
        [
            {"logged_at": now},
            {"logged_at": now - timedelta(days=1)},
        ]
    )
    logs.find.return_value = streak_logs
    logs.find_one.return_value = {
        "_id": inserted_id,
        "habit_id": sample_habit_dict["_id"],
        "user_id": sample_user_dict["_id"],
        "logged_at": now,
        "note": "done",
        "streak_count": 2,
    }
    result = log_service.log_habit(
        str(sample_user_dict["_id"]), str(sample_habit_dict["_id"]), "done"
    )
    assert result["note"] == "done"
    logs.insert_one.assert_called_once()


def test_get_30_day_summary_percentages(log_service, mock_db, sample_user_dict):
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    habit_id = ObjectId()
    habits.find.return_value = [
        {
            "_id": habit_id,
            "user_id": sample_user_dict["_id"],
            "name": "Run",
        }
    ]
    now = datetime.now(timezone.utc)
    logs.find.return_value = [
        {"logged_at": now},
        {"logged_at": now - timedelta(days=1)},
    ]
    summary = log_service.get_30_day_summary(str(sample_user_dict["_id"]))
    assert len(summary) == 1
    assert summary[0]["habit_id"] == str(habit_id)
    assert summary[0]["completion_rate"] > 0
