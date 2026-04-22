# backend/app/models/user.py
"""User domain model with bcrypt password hashing."""

import re
from datetime import datetime, timezone

import bcrypt


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User:
    """Represents an application user."""

    def __init__(self, full_name, email, password, password_hash=None):
        self.full_name = full_name.strip()
        self.email = email.strip().lower()
        if not _EMAIL_RE.match(self.email):
            raise ValueError("Invalid email format")
        if password_hash:
            self.password_hash = password_hash
        else:
            if not password:
                raise ValueError("Password is required")
            self.password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

    def verify_password(self, plain):
        """Return True if plain password matches the stored hash."""
        return bcrypt.checkpw(
            plain.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self, include_hash=False):
        """Serialize user for API or storage."""
        data = {
            "full_name": self.full_name,
            "email": self.email,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "preferences": {"reminder_time": "09:00", "theme": "light"},
        }
        if include_hash:
            data["password_hash"] = self.password_hash
        return data

    @classmethod
    def from_dict(cls, data):
        """Hydrate a User instance from a Mongo document."""
        return cls(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            password=None,
            password_hash=data.get("password_hash"),
        )
