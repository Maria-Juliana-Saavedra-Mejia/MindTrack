# backend/app/models/user.py
"""User domain model (password stored as plain text for local/demo use)."""

import re
from datetime import datetime, timezone

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User:
    """Represents an application user."""

    def __init__(self, full_name, email, password=None, stored_password=None):
        self.full_name = full_name.strip()
        self.email = email.strip().lower()
        if not _EMAIL_RE.match(self.email):
            raise ValueError("Invalid email format")
        if stored_password is not None:
            self.password = stored_password
        elif password:
            self.password = password
        else:
            raise ValueError("Password is required")

    def verify_password(self, plain):
        """Return True if plain password matches the stored value."""
        return self.password == plain

    def to_dict(self, include_password=False):
        """Serialize user for API or storage."""
        data = {
            "full_name": self.full_name,
            "email": self.email,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "preferences": {"reminder_time": "09:00", "theme": "light"},
        }
        if include_password:
            data["password"] = self.password
        return data

    @classmethod
    def from_dict(cls, data):
        """Hydrate a User instance from a Mongo document."""
        # `password` is the canonical field (plain text in this project). `password_hash`
        # is only an alternate key for legacy imports; the value is still compared as plain text.
        return cls(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            stored_password=data.get("password") or data.get("password_hash"),
        )
