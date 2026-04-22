# app/services/habit_service.py
"""Habit CRUD and streak calculations."""

from datetime import timezone

from bson import ObjectId

from app.models.habit import Habit
from app.utils.error_handlers import HabitNotFoundError, UnauthorizedError


class HabitService:
    """Business logic for habits."""

    def __init__(self, db):
        self._habits = db["habits"]
        self._logs = db["habit_logs"]

    def create_habit(self, user_id, data):
        """Persist a new habit for the user."""
        habit = Habit(
            user_id=ObjectId(str(user_id)),
            name=(data or {}).get("name", ""),
            description=(data or {}).get("description", ""),
            frequency=(data or {}).get("frequency"),
            category=(data or {}).get("category"),
            color=(data or {}).get("color", "#0F6E56"),
            icon=(data or {}).get("icon", "✅"),
            is_active=(data or {}).get("is_active", True),
        )
        doc = habit.to_dict()
        result = self._habits.insert_one(doc)
        created = self._habits.find_one({"_id": result.inserted_id})
        return self._serialize(created)

    def get_habits(self, user_id, active_only=False):
        """Return all habits for a user."""
        query = {"user_id": ObjectId(str(user_id))}
        if active_only:
            query["is_active"] = True
        habits = self._habits.find(query).sort("created_at", -1)
        return [self._serialize(h) for h in habits]

    def get_habit(self, habit_id, user_id):
        """Return a single habit if owned by user."""
        habit = self._habits.find_one({"_id": self._oid(habit_id)})
        if not habit:
            raise HabitNotFoundError("Habit not found")
        if str(habit["user_id"]) != str(user_id):
            raise UnauthorizedError("Cannot access this habit")
        return self._serialize(habit)

    def update_habit(self, habit_id, user_id, data):
        """Update fields on a habit."""
        habit = self._habits.find_one({"_id": self._oid(habit_id)})
        if not habit:
            raise HabitNotFoundError("Habit not found")
        if str(habit["user_id"]) != str(user_id):
            raise UnauthorizedError("Cannot update this habit")
        updates = {}
        for key in ("name", "description", "frequency", "category", "color", "icon", "is_active"):
            if key in (data or {}):
                updates[key] = data[key]
        if "frequency" in updates and updates["frequency"] not in Habit.VALID_FREQUENCIES:
            raise ValueError("Invalid frequency")
        if "category" in updates and updates["category"] not in Habit.VALID_CATEGORIES:
            raise ValueError("Invalid category")
        if updates:
            self._habits.update_one({"_id": habit["_id"]}, {"$set": updates})
        refreshed = self._habits.find_one({"_id": habit["_id"]})
        return self._serialize(refreshed)

    def delete_habit(self, habit_id, user_id):
        """Delete a habit owned by the user."""
        habit = self._habits.find_one({"_id": self._oid(habit_id)})
        if not habit:
            raise HabitNotFoundError("Habit not found")
        if str(habit["user_id"]) != str(user_id):
            raise UnauthorizedError("Cannot delete this habit")
        self._habits.delete_one({"_id": habit["_id"]})
        self._logs.delete_many({"habit_id": habit["_id"]})

    def calculate_streak(self, habit_id):
        """Return consecutive-day streak for a habit."""
        hid = self._oid(habit_id)
        logs = self._logs.find({"habit_id": hid}).sort("logged_at", -1)
        dates = []
        for log in logs:
            dt = log.get("logged_at")
            if not dt:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            day = dt.astimezone(timezone.utc).date()
            dates.append(day)
        unique_sorted = sorted(set(dates), reverse=True)
        if not unique_sorted:
            return 0
        streak = 1
        for i in range(1, len(unique_sorted)):
            prev = unique_sorted[i - 1]
            cur = unique_sorted[i]
            if (prev - cur).days == 1:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def _serialize(doc):
        return {
            "id": str(doc["_id"]),
            "user_id": str(doc["user_id"]),
            "name": doc.get("name"),
            "description": doc.get("description", ""),
            "frequency": doc.get("frequency"),
            "category": doc.get("category"),
            "color": doc.get("color"),
            "icon": doc.get("icon"),
            "created_at": doc.get("created_at").isoformat()
            if doc.get("created_at")
            else None,
            "is_active": doc.get("is_active", True),
        }

    @staticmethod
    def _oid(value):
        try:
            return ObjectId(str(value))
        except Exception as exc:
            raise HabitNotFoundError("Invalid habit id") from exc
