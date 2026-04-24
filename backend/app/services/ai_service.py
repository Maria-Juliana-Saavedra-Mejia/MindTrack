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

    def seed_starter_insight_after_first_log(self, user_id, habit_name):
        """
        After the user's first habit log ever, insert a welcoming coach message
        (no OpenAI call) so the dashboard shows guidance immediately.
        """
        uid = ObjectId(str(user_id))
        safe = (habit_name or "your habit").strip()[:120] or "your habit"
        if self._logs.count_documents({"user_id": uid}) != 1:
            return None
        if self._insights.find_one({"user_id": uid}):
            return None
        generated_at = datetime.now(timezone.utc)
        compliment = (
            f"You logged your first completion on “{safe}.” "
            "That first step is the hardest—and you already took it."
        )
        observation = (
            "Momentum builds one tap at a time. Showing up today already puts you "
            "ahead of waiting for the perfect moment."
        )
        tip = (
            f"Try pairing “{safe}” with a fixed cue (after class, after coffee, "
            "before bed) so the next log feels automatic."
        )
        doc = {
            "user_id": uid,
            "generated_at": generated_at,
            "insight_type": "starter",
            "compliment": compliment,
            "observation": observation,
            "tip": tip,
            "content": json.dumps(
                {"compliment": compliment, "observation": observation, "tip": tip}
            ),
            "habits_analyzed": [],
        }
        self._insights.insert_one(doc)
        return {
            "compliment": compliment,
            "observation": observation,
            "tip": tip,
            "generated_at": generated_at.isoformat(),
            "insight_type": "starter",
        }

    def generate_insights(self, user_id):
        """Create a new AI insight document based on recent activity."""
        uid = ObjectId(str(user_id))
        habits = list(self._habits.find({"user_id": uid, "is_active": True}))
        if not habits:
            raise ValueError("No active habits to analyze")
        total_logs = self._logs.count_documents({"user_id": uid})
        early = total_logs < 20
        window_days = 30 if early else 14
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=window_days)
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
            rate = round((len(days) / window_days) * 100, 2)
            completion_parts.append(f"{name}: {rate}% active-day coverage")
            streak = self._calculate_streak_for_habit(hid)
            best_streak = max(best_streak, streak)
            if lowest_rate is None or rate < lowest_rate:
                lowest_rate = rate
                lowest_habit = name
        habits_block = ", ".join(habit_lines)
        completion_block = "; ".join(completion_parts)
        most_missed = lowest_habit or habits[0].get("name")
        time_label = f"last ~{window_days} days" if early else "past 2 weeks"
        user_prompt = (
            f"Here is my habit data for the {time_label}:\n"
            f"Habits: {habits_block}\n"
            f"Activity (share of days in window with at least one log): {completion_block}\n"
            f"Best streak across habits: {best_streak} days\n"
            f"Lowest activity signal: {most_missed}\n"
        )
        if early:
            user_prompt += (
                f"\nThe user is fairly new (about {total_logs} total check-ins). "
                "Celebrate small wins, avoid harsh judgment, and keep advice practical.\n"
            )
        user_prompt += (
            "\nGive me exactly 3 things:\n"
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
        insight_type = "early" if early else "suggestion"
        doc = {
            "user_id": uid,
            "generated_at": generated_at,
            "insight_type": insight_type,
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
            "insight_type": insight_type,
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
