# backend/tests/test_ai_service.py
"""Tests for AIService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from tests.conftest import FakeCursor


@pytest.fixture
def ai_service(mock_db, monkeypatch):
    from app.services.ai_service import AIService

    service = AIService(mock_db, openai_api_key="sk-test")
    fake_client = MagicMock()
    service._client = fake_client
    return service


def test_seed_starter_insight_after_first_log(ai_service, mock_db, sample_user_dict):
    logs = mock_db["habit_logs"]
    insights = mock_db["ai_insights"]
    logs.count_documents.return_value = 1
    insights.find_one.return_value = None
    out = ai_service.seed_starter_insight_after_first_log(
        str(sample_user_dict["_id"]), "Morning run"
    )
    assert out is not None
    assert "Morning run" in out["compliment"]
    assert out["insight_type"] == "starter"
    insights.insert_one.assert_called_once()


def test_seed_starter_skips_when_not_first_log(ai_service, mock_db, sample_user_dict):
    logs = mock_db["habit_logs"]
    logs.count_documents.return_value = 3
    out = ai_service.seed_starter_insight_after_first_log(
        str(sample_user_dict["_id"]), "Run"
    )
    assert out is None


def test_generate_insights_accepts_iso_string_logged_at(ai_service, mock_db, sample_user_dict):
    """Mongo or imports may surface log times as ISO strings; generation must not crash."""
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    insights = mock_db["ai_insights"]
    habit_id = ObjectId()
    logs.count_documents.return_value = 5
    habits.find.return_value = [
        {
            "_id": habit_id,
            "name": "Run",
            "category": "health",
            "user_id": sample_user_dict["_id"],
            "is_active": True,
        }
    ]
    logs.find.return_value = FakeCursor(
        [{"logged_at": "2024-01-05T12:00:00+00:00"}]
    )
    ai_service._client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"compliment":"A","observation":"B","tip":"C"}'
                )
            )
        ]
    )
    result = ai_service.generate_insights_openai(str(sample_user_dict["_id"]))
    assert result["compliment"] == "A"
    insights.insert_one.assert_called_once()


def test_generate_insights_calls_openai(ai_service, mock_db, sample_user_dict):
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    insights = mock_db["ai_insights"]
    habit_id = ObjectId()
    logs.count_documents.return_value = 50
    habits.find.return_value = [
        {
            "_id": habit_id,
            "name": "Run",
            "category": "health",
            "user_id": sample_user_dict["_id"],
            "is_active": True,
        }
    ]
    logs.find.return_value = FakeCursor([])
    ai_service._client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"compliment":"Nice","observation":"Gap","tip":"Plan"}'
                )
            )
        ]
    )
    result = ai_service.generate_insights_openai(str(sample_user_dict["_id"]))
    assert result["compliment"] == "Nice"
    ai_service._client.chat.completions.create.assert_called_once()
    args, kwargs = ai_service._client.chat.completions.create.call_args
    messages = kwargs["messages"]
    user_message = messages[1]["content"]
    assert "Run" in user_message and "health" in user_message
    insights.insert_one.assert_called_once()
    inserted = insights.insert_one.call_args[0][0]
    assert inserted["compliment"] == "Nice"
    assert inserted["insight_type"] == "suggestion"
    assert inserted["observation"] == "Gap"
    assert inserted["tip"] == "Plan"


def test_get_latest_insights_returns_recent(ai_service, mock_db, sample_user_dict):
    insights = mock_db["ai_insights"]
    insights.find_one.return_value = {
        "compliment": "Great",
        "observation": "Keep going",
        "tip": "Stretch",
        "generated_at": datetime.now(timezone.utc),
        "insight_type": "suggestion",
        "habits_analyzed": [ObjectId()],
    }
    latest = ai_service.get_latest_insights(str(sample_user_dict["_id"]))
    assert latest["compliment"] == "Great"
    insights.find_one.assert_called_once()


def test_generate_insights_template_no_openai(ai_service, mock_db, sample_user_dict):
    """Offline template path inserts insight without calling OpenAI."""
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    insights = mock_db["ai_insights"]
    habit_id = ObjectId()
    logs.count_documents.return_value = 8
    habits.find.return_value = [
        {
            "_id": habit_id,
            "name": "Read",
            "category": "study",
            "user_id": sample_user_dict["_id"],
            "is_active": True,
        }
    ]
    logs.find.return_value = FakeCursor(
        [{"logged_at": datetime.now(timezone.utc).isoformat()}]
    )
    result = ai_service.generate_insights_template(str(sample_user_dict["_id"]))
    assert result["insight_type"] == "template"
    assert result["compliment"]
    assert result["observation"]
    assert result["tip"]
    insights.insert_one.assert_called_once()
    ai_service._client.chat.completions.create.assert_not_called()


def test_get_latest_insights_string_generated_at(ai_service, mock_db, sample_user_dict):
    insights = mock_db["ai_insights"]
    iso = "2024-01-01T00:00:00+00:00"
    insights.find_one.return_value = {
        "compliment": "x",
        "observation": "y",
        "tip": "z",
        "generated_at": iso,
        "insight_type": "starter",
        "habits_analyzed": [],
    }
    latest = ai_service.get_latest_insights(str(sample_user_dict["_id"]))
    assert latest["generated_at"] == iso
