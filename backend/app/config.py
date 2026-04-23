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

    @staticmethod
    def _runtime_env_name():
        """'production' in deploy hosts; set FLASK_ENV=production (or ENV=production)."""
        e = (os.getenv("FLASK_ENV") or os.getenv("ENV") or "development").strip().lower()
        if e in ("prod", "production"):
            return "production"
        return e

    @classmethod
    def fastapi_cors_middleware_options(cls):
        """
        Kwargs for Starlette CORSMiddleware. Set CORS_ORIGINS in production, e.g.:
        CORS_ORIGINS=https://user.github.io,https://app.example.com
        (comma-separated browser origins, no /api path). If unset, non-production
        allows any origin (*) so Live Server, localhost vs 127.0.0.1, and
        any port all work. Production with no CORS_ORIGINS = no CORS (set env to fix).
        """
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if raw:
            opts: dict = {
                "allow_origins": [o.strip() for o in raw.split(",") if o.strip()],
                "allow_origin_regex": None,
                "allow_credentials": False,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }
            if cls._runtime_env_name() != "production":
                # Allow Live Server / preview on any loopback port (e.g. :5500) to read GET
                # /mindtrack-http-port during api.js discovery when CORS_ORIGINS is an explicit list.
                opts["allow_origin_regex"] = (
                    r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
                )
            return opts
        if cls._runtime_env_name() == "production":
            return {
                "allow_origins": [],
                "allow_origin_regex": None,
                "allow_credentials": False,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }
        return {
            "allow_origins": ["*"],
            "allow_origin_regex": None,
            "allow_credentials": False,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    @staticmethod
    def mongo_client_kwargs():
        """
        TLS options for PyMongo (Atlas uses TLS).

        Uses certifi's CA bundle so Python can verify Atlas certificates when the
        interpreter's default trust store is incomplete (common on macOS).

        Set MONGO_TLS_INSECURE=1 only for local development if verification still fails
        (disables certificate validation; never use in production).
        """
        insecure = os.getenv("MONGO_TLS_INSECURE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if insecure:
            return {"tlsAllowInvalidCertificates": True}
        try:
            import certifi

            return {"tlsCAFile": certifi.where()}
        except ImportError:
            return {}

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
    def to_app_config(cls):
        """Merged settings dict (Mongo, JWT, OpenAI, log level) after validation."""
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
