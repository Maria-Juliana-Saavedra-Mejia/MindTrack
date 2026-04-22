# app/services/ai_service.py
"""AI-powered habit insights."""

import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from openai import OpenAI


class AIService:
    """Generates and retrieves AI insights."""

    def __init__(self, db, openai_api_key):
        self._db = db
        self._habits = db["habits"]
        self._logs = db["habit_logs"]
        self._insights = db["ai_insights"]
        self._client = OpenAI(api_key=openai_api_key)

    def generate_insights(self, user_id):
        """Create a new AI insight document based on recent activity."""
        uid = ObjectId(str(user_id))
        habits = list(self._habits.find({"user_id": uid, "is_active": True}))
        if not habits:
            raise ValueError("No active habits to analyze")
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=14)
        habit_lines = []
        completion_parts = []
        best_streak = 0
        lowest_rate = None
        lowest_habit = None
        for habit in habits:
            hid = habit["_id"]
            name = habit.get("name")
            category = habit.get("category")
            habit_lines.append(f"{name} ({category})")
            logs = list(
                self._logs.find(
                    {
                        "user_id": uid,
                        "habit_id": hid,
                        "logged_at": {"$gte": start, "$lte": end},
                    }
                )
            )
            days = set()
            for lg in logs:
                dt = lg.get("logged_at")
                if not dt:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                days.add(dt.astimezone(timezone.utc).date())
            rate = round((len(days) / 14) * 100, 2)
            completion_parts.append(f"{name}: {rate}% completed")
            streak = self._calculate_streak_for_habit(hid)
            best_streak = max(best_streak, streak)
            if lowest_rate is None or rate < lowest_rate:
                lowest_rate = rate
                lowest_habit = name
        habits_block = ", ".join(habit_lines)
        completion_block = "; ".join(completion_parts)
        most_missed = lowest_habit or habits[0].get("name")
        user_prompt = (
            "Here is my habit data for the past 2 weeks:\n"
            f"Habits: {habits_block}\n"
            f"Completion rates: {completion_block}\n"
            f"Best streak: {best_streak} days\n"
            f"Most missed habit: {most_missed}\n\n"
            "Give me exactly 3 things:\n"
            "1. One specific compliment about what I did well (1 sentence)\n"
            "2. One honest, gentle observation about my biggest gap (1 sentence)\n"
            "3. One concrete, actionable tip for next week (1-2 sentences)\n\n"
            'Format your response as JSON: { "compliment", "observation", "tip" }'
        )
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are MindTrack Coach, a warm and encouraging habit coach. "
                        "Be concise, specific, and positive."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        compliment = data.get("compliment", "")
        observation = data.get("observation", "")
        tip = data.get("tip", "")
        generated_at = datetime.now(timezone.utc)
        doc = {
            "user_id": uid,
            "generated_at": generated_at,
            "insight_type": "suggestion",
            "compliment": compliment,
            "observation": observation,
            "tip": tip,
            "content": json.dumps(
                {
                    "compliment": compliment,
                    "observation": observation,
                    "tip": tip,
                }
            ),
            "habits_analyzed": [h["_id"] for h in habits],
        }
        self._insights.insert_one(doc)
        return {
            "compliment": compliment,
            "observation": observation,
            "tip": tip,
            "generated_at": generated_at.isoformat(),
        }

    def get_latest_insights(self, user_id):
        """Return the most recent insight for a user."""
        uid = ObjectId(str(user_id))
        doc = self._insights.find_one(
            {"user_id": uid}, sort=[("generated_at", -1)]
        )
        if not doc:
            return None
        return {
            "compliment": doc.get("compliment"),
            "observation": doc.get("observation"),
            "tip": doc.get("tip"),
            "generated_at": doc.get("generated_at").isoformat()
            if doc.get("generated_at")
            else None,
            "insight_type": doc.get("insight_type"),
            "habits_analyzed": [str(h) for h in doc.get("habits_analyzed", [])],
        }

    def _calculate_streak_for_habit(self, habit_id):
        logs = self._logs.find({"habit_id": habit_id}).sort("logged_at", -1)
        dates = []
        for log in logs:
            dt = log.get("logged_at")
            if not dt:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dates.append(dt.astimezone(timezone.utc).date())
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
