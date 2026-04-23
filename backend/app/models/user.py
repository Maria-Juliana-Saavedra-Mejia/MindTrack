# backend/app/models/user.py
"""User domain model; persisted secret is bcrypt in ``password_hash`` (legacy plain supported)."""

import re
from datetime import datetime, timezone

from app.utils.passwords import verify_stored_password

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
        return verify_stored_password(plain, self.password)

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
        # Prefer bcrypt ``password_hash``; legacy docs may use ``password`` (plain).
        return cls(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            stored_password=data.get("password_hash") or data.get("password"),
        )
