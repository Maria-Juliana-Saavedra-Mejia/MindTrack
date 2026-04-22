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


def test_generate_insights_calls_openai(ai_service, mock_db, sample_user_dict):
    habits = mock_db["habits"]
    logs = mock_db["habit_logs"]
    insights = mock_db["ai_insights"]
    habit_id = ObjectId()
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
    result = ai_service.generate_insights(str(sample_user_dict["_id"]))
    assert result["compliment"] == "Nice"
    ai_service._client.chat.completions.create.assert_called_once()
    args, kwargs = ai_service._client.chat.completions.create.call_args
    messages = kwargs["messages"]
    user_message = messages[1]["content"]
    assert "Run" in user_message and "health" in user_message
    insights.insert_one.assert_called_once()
    inserted = insights.insert_one.call_args[0][0]
    assert inserted["compliment"] == "Nice"
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
