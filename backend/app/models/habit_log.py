# backend/app/models/habit_log.py
"""Habit log domain model."""

from datetime import datetime, timezone


class HabitLog:
    """Represents a single habit completion log."""

    def __init__(
        self,
        habit_id,
        user_id,
        note=None,
        logged_at=None,
        streak_count=0,
    ):
        self.habit_id = habit_id
        self.user_id = user_id
        self.note = note
        self.logged_at = logged_at or datetime.now(timezone.utc)
        self.streak_count = int(streak_count)

    def to_dict(self):
        """Serialize log for persistence."""
        return {
            "habit_id": self.habit_id,
            "user_id": self.user_id,
            "logged_at": self.logged_at,
            "note": self.note,
            "streak_count": self.streak_count,
        }
