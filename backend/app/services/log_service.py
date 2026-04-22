# app/services/log_service.py
"""Logging completions and querying history."""

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.models.habit_log import HabitLog
from app.utils.error_handlers import HabitNotFoundError, UnauthorizedError


class LogService:
    """Habit log operations."""

    def __init__(self, db, habit_service):
        self._logs = db["habit_logs"]
        self._habits = db["habits"]
        self._habit_service = habit_service

    def log_habit(self, user_id, habit_id, note=None):
        """Create a log entry after verifying habit ownership."""
        habit = self._habits.find_one({"_id": self._oid(habit_id)})
        if not habit:
            raise HabitNotFoundError("Habit not found")
        if str(habit["user_id"]) != str(user_id):
            raise UnauthorizedError("Cannot log for this habit")
        log = HabitLog(
            habit_id=habit["_id"],
            user_id=ObjectId(str(user_id)),
            note=note,
        )
        doc = log.to_dict()
        result = self._logs.insert_one(doc)
        inserted_id = result.inserted_id
        streak = self._habit_service.calculate_streak(habit_id)
        self._logs.update_one(
            {"_id": inserted_id},
            {"$set": {"streak_count": streak}},
        )
        inserted = self._logs.find_one({"_id": inserted_id})
        return self._serialize(inserted)

    def get_logs(self, user_id, filters=None):
        """Return logs with optional habit/date filters."""
        filters = filters or {}
        query = {"user_id": ObjectId(str(user_id))}
        if filters.get("habit_id"):
            query["habit_id"] = self._oid(filters["habit_id"])
        if filters.get("date_from") or filters.get("date_to"):
            rng = {}
            if filters.get("date_from"):
                rng["$gte"] = self._parse_dt(filters["date_from"])
            if filters.get("date_to"):
                rng["$lte"] = self._parse_dt(filters["date_to"])
            query["logged_at"] = rng
        cursor = self._logs.find(query).sort("logged_at", -1)
        return [self._serialize(doc) for doc in cursor]

    def delete_log(self, log_id, user_id):
        """Delete a log owned by the user."""
        try:
            oid = ObjectId(str(log_id))
        except Exception as exc:
            raise HabitNotFoundError("Log not found") from exc
        log = self._logs.find_one({"_id": oid})
        if not log:
            raise HabitNotFoundError("Log not found")
        if str(log["user_id"]) != str(user_id):
            raise UnauthorizedError("Cannot delete this log")
        self._logs.delete_one({"_id": log["_id"]})

    def get_streak(self, habit_id):
        """Return streak for a habit."""
        return self._habit_service.calculate_streak(habit_id)

    def get_30_day_summary(self, user_id):
        """Completion percentage per habit for the last 30 days."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        uid = ObjectId(str(user_id))
        habits = list(self._habits.find({"user_id": uid}))
        summary = []
        for habit in habits:
            hid = habit["_id"]
            logs = self._logs.find(
                {
                    "user_id": uid,
                    "habit_id": hid,
                    "logged_at": {"$gte": start, "$lte": end},
                }
            )
            days = set()
            for lg in logs:
                dt = lg.get("logged_at")
                if not dt:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                days.add(dt.astimezone(timezone.utc).date())
            rate = round((len(days) / 30) * 100, 2) if days else 0.0
            summary.append(
                {
                    "habit_id": str(hid),
                    "habit_name": habit.get("name"),
                    "completion_rate": rate,
                }
            )
        return summary

    def _serialize(self, doc):
        if not doc:
            return {}
        return {
            "id": str(doc["_id"]),
            "habit_id": str(doc["habit_id"]),
            "user_id": str(doc["user_id"]),
            "logged_at": doc.get("logged_at").isoformat()
            if doc.get("logged_at")
            else None,
            "note": doc.get("note"),
            "streak_count": doc.get("streak_count", 0),
        }

    @staticmethod
    def _oid(value):
        try:
            return ObjectId(str(value))
        except Exception as exc:
            raise HabitNotFoundError("Invalid id") from exc

    @staticmethod
    def _parse_dt(value):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception as exc:
            raise ValueError("Invalid date format") from exc
