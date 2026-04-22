# backend/tests/test_auth_service.py
"""Tests for AuthService."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.utils.error_handlers import InvalidCredentialsError, UserAlreadyExistsError


def test_register_success(auth_service, mock_db):
    users = mock_db["users"]
    users.find_one.return_value = None
    inserted_id = ObjectId()
    users.insert_one.return_value = MagicMock(inserted_id=inserted_id)
    users.find_one.side_effect = [
        None,
        {
            "_id": inserted_id,
            "full_name": "New User",
            "email": "new@example.com",
            "password": "password123",
            "preferences": {"reminder_time": "09:00", "theme": "light"},
            "created_at": None,
            "last_login": None,
        },
    ]
    payload = {
        "full_name": "New User",
        "email": "new@example.com",
        "password": "password123",
    }
    user = auth_service.register_user(payload)
    assert user["email"] == "new@example.com"
    users.insert_one.assert_called_once()


def test_register_duplicate_email_raises(auth_service, mock_db):
    users = mock_db["users"]
    users.find_one.return_value = {"email": "exists@example.com"}
    with pytest.raises(UserAlreadyExistsError):
        auth_service.register_user(
            {
                "full_name": "A",
                "email": "exists@example.com",
                "password": "password123",
            }
        )


def test_login_wrong_password_raises(auth_service, mock_db, sample_user_dict):
    users = mock_db["users"]
    users.find_one.return_value = sample_user_dict
    with pytest.raises(InvalidCredentialsError):
        auth_service.login_user("user@example.com", "wrongpassword")


def test_login_unknown_email_raises(auth_service, mock_db):
    users = mock_db["users"]
    users.find_one.return_value = None
    with pytest.raises(InvalidCredentialsError):
        auth_service.login_user("missing@example.com", "password123")
