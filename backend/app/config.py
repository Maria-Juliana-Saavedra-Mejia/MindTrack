# backend/app/config.py
"""Environment-driven configuration for MindTrack."""

import os

# Used only when JWT_SECRET is not set in the process environment.
# For production, set JWT_SECRET on your host (do not rely on this value).
_DEV_JWT_SECRET = (
    "mindtrack-dev-only-jwt-secret-change-in-production-minimum-32-chars"
)

# Used only when OPENAI_API_KEY is not set. Real AI calls need a valid key
# from your hosting environment.
_DEV_OPENAI_API_KEY = "sk-dev-placeholder-not-for-production-openai-calls"


class Config:
    """Loads settings from environment variables when validated or exported."""

    @staticmethod
    def _mongo_uri():
        """Mongo connection URI; trailing slashes stripped (common with Atlas)."""
        uri = os.getenv("MONGO_URI", "").strip()
        return uri.rstrip("/")

    @staticmethod
    def _mongo_db_name():
        return os.getenv("MONGO_DB_NAME", "").strip()

    @staticmethod
    def _jwt_secret():
        return os.getenv("JWT_SECRET", "").strip() or _DEV_JWT_SECRET

    @staticmethod
    def _openai_key():
        return os.getenv("OPENAI_API_KEY", "").strip() or _DEV_OPENAI_API_KEY

    @staticmethod
    def _jwt_expiry_hours():
        return int(os.getenv("JWT_EXPIRY_HOURS", "24") or "24")

    @staticmethod
    def _flask_env():
        return os.getenv("FLASK_ENV", "development").strip()

    @staticmethod
    def _log_level():
        return os.getenv("LOG_LEVEL", "INFO").strip()

    @classmethod
    def validate(cls):
        """Require Mongo connection URI and database name (.env)."""
        missing = []
        if not cls._mongo_uri():
            missing.append("MONGO_URI")
        if not cls._mongo_db_name():
            missing.append("MONGO_DB_NAME")
        if missing:
            raise EnvironmentError(
                "Missing required environment variables: " + ", ".join(missing)
            )

    @classmethod
    def to_flask_config(cls):
        """Map to Flask config keys."""
        cls.validate()
        return {
            "MONGO_URI": cls._mongo_uri(),
            "MONGO_DB_NAME": cls._mongo_db_name(),
            "JWT_SECRET": cls._jwt_secret(),
            "JWT_EXPIRY_HOURS": cls._jwt_expiry_hours(),
            "OPENAI_API_KEY": cls._openai_key(),
            "DEBUG": cls._flask_env().lower() == "development",
            "LOG_LEVEL": cls._log_level(),
        }
