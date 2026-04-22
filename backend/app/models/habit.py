# backend/app/models/habit.py
"""Habit domain model."""

from datetime import datetime, timezone


class Habit:
    """Represents a habit owned by a user."""

    VALID_FREQUENCIES = ("daily", "weekly")
    VALID_CATEGORIES = ("health", "productivity", "mindfulness", "other")

    def __init__(
        self,
        user_id,
        name,
        description,
        frequency,
        category,
        color,
        icon,
        is_active=True,
        created_at=None,
    ):
        self.user_id = user_id
        self.name = name.strip()
        self.description = (description or "").strip()
        self.frequency = frequency
        self.category = category
        self.color = color
        self.icon = icon
        self.is_active = bool(is_active)
        self.created_at = created_at or datetime.now(timezone.utc)
        if not self.is_valid():
            raise ValueError("Invalid habit data")

    def is_valid(self):
        """Return True if frequency and category are allowed."""
        return (
            self.frequency in self.VALID_FREQUENCIES
            and self.category in self.VALID_CATEGORIES
            and bool(self.name)
        )

    def to_dict(self):
        """Serialize habit for persistence."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency,
            "category": self.category,
            "color": self.color,
            "icon": self.icon,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Habit from stored data."""
        return cls(
            user_id=data.get("user_id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            frequency=data.get("frequency"),
            category=data.get("category"),
            color=data.get("color", "#0F6E56"),
            icon=data.get("icon", "✅"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
        )
