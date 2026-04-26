# app/services/ai_service.py
"""AI-powered habit insights."""

import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from openai import OpenAI


def _format_generated_at(value):
    """Mongo may store UTC datetimes; tolerate legacy string values."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


def ephemeral_insight_payload(kind: str = "persist_failed") -> dict:
    """
    Coach-style JSON returned with HTTP 200 when we cannot write to MongoDB or when
    the server is misconfigured for OpenAI-only mode. Not stored — GET /insights may
    still show an older saved insight until persistence works again.
    """
    now = datetime.now(timezone.utc).isoformat()
    if kind == "openai_key_required":
        return {
            "compliment": (
                "This server is set to use OpenAI for coach notes, but no API key is configured yet."
            ),
            "observation": (
                "On Render, add environment variable OPENAI_API_KEY, or set "
                "MINDTRACK_INSIGHT_PROVIDER=auto (the default) to use free template insights without a key."
            ),
            "tip": (
                "After changing environment variables on your host, trigger a new deploy so the "
                "service picks them up."
            ),
            "generated_at": now,
            "insight_type": "ephemeral",
        }
    return {
        "compliment": (
            "We could not save this coach note to the database right now, but you can still "
            "log habits and use the rest of MindTrack."
        ),
        "observation": (
            "This usually means MongoDB is unreachable from the API (wrong MONGO_URI, Atlas IP "
            "allowlist, or the database is paused). Fix the connection on your host and try again."
        ),
        "tip": (
            "Check Render logs for the exact error, confirm MONGO_URI and MONGO_DB_NAME in "
            "environment variables, and that your Atlas cluster allows Render’s outbound IPs."
        ),
        "generated_at": now,
        "insight_type": "ephemeral",
    }


def _coerce_utc_datetime(value):
    """Normalize habit log timestamps for streak and coverage math."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

    def _collect_insight_context(self, user_id):
        """Shared habit stats for OpenAI prompts and offline template coach."""
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
        lowest_habit_name = None
        habit_stats = []
        for habit in habits:
            hid = habit["_id"]
            name = habit.get("name")
            category = habit.get("category") or ""
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
                dt = _coerce_utc_datetime(lg.get("logged_at"))
                if not dt:
                    continue
                days.add(dt.date())
            rate = round((len(days) / window_days) * 100, 2)
            completion_parts.append(f"{name}: {rate}% active-day coverage")
            streak = self._calculate_streak_for_habit(hid)
            best_streak = max(best_streak, streak)
            if lowest_rate is None or rate < lowest_rate:
                lowest_rate = rate
                lowest_habit_name = name
            habit_stats.append(
                {
                    "name": name,
                    "category": category,
                    "habit_id": hid,
                    "rate": rate,
                    "streak": streak,
                    "days_in_window": len(days),
                }
            )
        most_missed = lowest_habit_name or habits[0].get("name")
        return {
            "user_id": str(user_id),
            "uid": uid,
            "habits": habits,
            "total_logs": total_logs,
            "early": early,
            "window_days": window_days,
            "start": start,
            "end": end,
            "best_streak": best_streak,
            "lowest_rate": lowest_rate if lowest_rate is not None else 0.0,
            "most_missed": most_missed,
            "habit_stats": habit_stats,
            "habits_block": ", ".join(habit_lines),
            "completion_block": "; ".join(completion_parts),
        }

    def _variety_index(self, user_id: str) -> int:
        """Stable-enough index to rotate template phrasing between refreshes."""
        t = int(datetime.now(timezone.utc).timestamp())
        return abs(hash(f"{user_id}:{t}")) % 10000

    def _build_template_coach(self, ctx):
        """Deterministic friendly coach copy without calling OpenAI."""
        idx = self._variety_index(ctx["user_id"])
        names = [
            (h.get("name") if isinstance(h.get("name"), str) else None) or "your habit"
            for h in ctx["habit_stats"]
        ]
        primary = (names[0] if names else "your habit").strip() or "your habit"
        best = ctx["best_streak"]
        early = ctx["early"]
        total_logs = ctx["total_logs"]
        raw_missed = ctx.get("most_missed")
        most_label = (
            (raw_missed if isinstance(raw_missed, str) else None)
            or primary
            or "your habit"
        )
        most_label = most_label.strip() or "your habit"
        low = ctx["lowest_rate"]
        window = ctx["window_days"]
        avg_rate = (
            sum(h["rate"] for h in ctx["habit_stats"]) / len(ctx["habit_stats"])
            if ctx["habit_stats"]
            else 0.0
        )

        if best >= 14:
            compliments = [
                f"Keeping momentum on “{primary}” with a {best}-day streak signal shows real discipline.",
                f"A {best}-day best streak is not luck—it is repeated choices in your favor.",
                "Your longest streak shows you already know how to show up more than once.",
            ]
        elif best >= 7:
            compliments = [
                "A week-plus streak on one of your habits proves you can chain good days together.",
                "You have already crossed the ‘this is becoming normal’ threshold on at least one habit.",
            ]
        elif early:
            compliments = [
                f"With about {total_logs} check-ins, you are in the early building phase—and you are still here.",
                "Starting is the part most people skip; you are collecting real data on yourself.",
                "Small logs add up; you are already training the habit of checking in.",
            ]
        elif avg_rate >= 50:
            compliments = [
                "You are logging on most days in this window—that consistency is hard to fake.",
                "Your recent activity shows you are treating these habits as part of the week, not a whim.",
            ]
        else:
            compliments = [
                "You still have active habits in play, which means the story is not finished.",
                "Showing up in the app—even on lighter weeks—keeps the loop alive for a comeback.",
            ]
        compliment = compliments[idx % len(compliments)]

        any_logs = any(h["days_in_window"] > 0 for h in ctx["habit_stats"])
        if not any_logs:
            observation = (
                f"In the last ~{window} days there were no logs yet—pick one tiny action "
                f"for “{most_label}” so the calendar stops looking empty."
            )
        elif low < 15:
            observation = (
                f"“{most_label}” has the lightest footprint in this window—"
                "that is your clearest lever if you want one focused win."
            )
        elif low < 35:
            observation = (
                f"Coverage is uneven; “{most_label}” is the habit most asking for a gentler plan or clearer cue."
            )
        else:
            observation = (
                "Your habits are all getting some airtime; the next level is making the easiest one feel automatic."
            )

        tips = [
            f"Anchor “{primary}” to something you already do daily (after brushing teeth, after lunch).",
            f"Lower the bar for “{most_label}”: two minutes counts—log it, then stop if you need to.",
            "Pick one habit as the ‘non-negotiable’ this week and protect it like a class you cannot skip.",
            "Review your cues: if evenings fail, try a morning slot for the hardest habit.",
            f"Stack “{primary}” with an existing routine so willpower is not doing all the work.",
            "Use one weekly review: three taps in MindTrack beats a vague plan in your head.",
        ]
        tip = tips[idx % len(tips)]

        return compliment, observation, tip

    def _persist_insight_doc(
        self,
        uid,
        compliment,
        observation,
        tip,
        insight_type,
        habits_analyzed,
    ):
        generated_at = datetime.now(timezone.utc)
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
            "habits_analyzed": habits_analyzed,
        }
        self._insights.insert_one(doc)
        return {
            "compliment": compliment,
            "observation": observation,
            "tip": tip,
            "generated_at": generated_at.isoformat(),
            "insight_type": insight_type,
        }

    def generate_insights_template(self, user_id):
        """Create a coach insight from templates (no external AI)."""
        ctx = self._collect_insight_context(user_id)
        compliment, observation, tip = self._build_template_coach(ctx)
        habits_analyzed = [h["_id"] for h in ctx["habits"]]
        return self._persist_insight_doc(
            ctx["uid"],
            compliment,
            observation,
            tip,
            "template",
            habits_analyzed,
        )

    def generate_emergency_static_insight(self, user_id):
        """
        Short fixed coach copy when statistics-based templates cannot be built.
        Still persisted so GET /api/ai/insights stays consistent.
        """
        uid = ObjectId(str(user_id))
        compliment = (
            "The personalized coach is temporarily unavailable, but you are still "
            "making progress by tracking your habits here."
        )
        observation = (
            "When the AI service hiccups, the logs you already saved still tell the truth "
            "about your week—nothing erases that."
        )
        tip = (
            "Try “New insight” again in a little while. If it keeps failing, you can still "
            "log completions and review your streaks on the dashboard."
        )
        return self._persist_insight_doc(
            uid,
            compliment,
            observation,
            tip,
            "template",
            [],
        )

    def generate_insights_openai(self, user_id):
        """Create a new AI insight document using OpenAI."""
        ctx = self._collect_insight_context(user_id)
        time_label = f"last ~{ctx['window_days']} days" if ctx["early"] else "past 2 weeks"
        user_prompt = (
            f"Here is my habit data for the {time_label}:\n"
            f"Habits: {ctx['habits_block']}\n"
            f"Activity (share of days in window with at least one log): {ctx['completion_block']}\n"
            f"Best streak across habits: {ctx['best_streak']} days\n"
            f"Lowest activity signal: {ctx['most_missed']}\n"
        )
        if ctx["early"]:
            user_prompt += (
                f"\nThe user is fairly new (about {ctx['total_logs']} total check-ins). "
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
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("AI returned no completion")
        msg = getattr(choices[0], "message", None)
        raw_content = getattr(msg, "content", None) if msg is not None else None
        content = (raw_content if isinstance(raw_content, str) else None) or "{}"
        data = json.loads(content)
        compliment = data.get("compliment", "")
        observation = data.get("observation", "")
        tip = data.get("tip", "")
        insight_type = "early" if ctx["early"] else "suggestion"
        habits_analyzed = [h["_id"] for h in ctx["habits"]]
        return self._persist_insight_doc(
            ctx["uid"],
            compliment,
            observation,
            tip,
            insight_type,
            habits_analyzed,
        )

    def generate_insights(self, user_id):
        """Backward-compatible alias for OpenAI-backed generation."""
        return self.generate_insights_openai(user_id)

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
            "generated_at": _format_generated_at(doc.get("generated_at")),
            "insight_type": doc.get("insight_type"),
            "habits_analyzed": [str(h) for h in doc.get("habits_analyzed", [])],
        }

    def _calculate_streak_for_habit(self, habit_id):
        logs = self._logs.find({"habit_id": habit_id}).sort("logged_at", -1)
        dates = []
        for log in logs:
            dt = _coerce_utc_datetime(log.get("logged_at"))
            if not dt:
                continue
            dates.append(dt.date())
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
