# backend/tests/test_habit_service.py
"""Tests for HabitService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.utils.error_handlers import UnauthorizedError
from tests.conftest import FakeCursor


def test_create_habit_success(habit_service, mock_db, sample_user_dict):
    habits = mock_db["habits"]
    inserted_id = ObjectId()
    habits.insert_one.return_value = MagicMock(inserted_id=inserted_id)
    habits.find_one.return_value = {
        "_id": inserted_id,
        "user_id": sample_user_dict["_id"],
        "name": "Meditate",
        "description": "",
        "frequency": "daily",
        "category": "mindfulness",
        "color": "#123456",
        "icon": "🧘",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    data = habit_service.create_habit(
        str(sample_user_dict["_id"]),
        {
            "name": "Meditate",
            "description": "",
            "frequency": "daily",
            "category": "mindfulness",
            "color": "#123456",
            "icon": "🧘",
        },
    )
    assert data["name"] == "Meditate"


def test_create_habit_invalid_frequency_raises(habit_service, mock_db, sample_user_dict):
    with pytest.raises(ValueError):
        habit_service.create_habit(
            str(sample_user_dict["_id"]),
            {
                "name": "Bad",
                "description": "",
                "frequency": "hourly",
                "category": "health",
                "color": "#fff",
                "icon": "✅",
            },
        )


def test_delete_habit_wrong_user_raises(habit_service, mock_db, sample_habit_dict):
    habits = mock_db["habits"]
    habits.find_one.return_value = sample_habit_dict
    other_user = ObjectId()
    with pytest.raises(UnauthorizedError):
        habit_service.delete_habit(str(sample_habit_dict["_id"]), str(other_user))


def test_calculate_streak_consecutive_days(habit_service, mock_db, sample_habit_dict):
    logs = mock_db["habit_logs"]
    base = datetime(2024, 1, 5, 10, 0, tzinfo=timezone.utc)
    entries = [
        {"logged_at": base},
        {"logged_at": base - timedelta(days=1)},
        {"logged_at": base - timedelta(days=2)},
    ]
    logs.find.return_value = FakeCursor(entries)
    streak = habit_service.calculate_streak(str(sample_habit_dict["_id"]))
    assert streak == 3


def test_calculate_streak_resets_after_gap(habit_service, mock_db, sample_habit_dict):
    logs = mock_db["habit_logs"]
    base = datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc)
    entries = [
        {"logged_at": base},
        {"logged_at": base - timedelta(days=2)},
    ]
    logs.find.return_value = FakeCursor(entries)
    streak = habit_service.calculate_streak(str(sample_habit_dict["_id"]))
    assert streak == 1
