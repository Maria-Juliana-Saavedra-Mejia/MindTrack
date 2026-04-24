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

# VS Code Live Server → FastAPI cross-origin dev (when CORS_ORIGINS is unset).
_DEFAULT_DEV_CORS_ORIGIN = "http://127.0.0.1:5500"

_CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]


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
        Kwargs for Starlette CORSMiddleware.

        - Non-production, no CORS_ORIGINS: allow only Live Server at _DEFAULT_DEV_CORS_ORIGIN.
        - CORS_ORIGINS set: comma-separated explicit origins (include Live Server if needed).
        - Production, no CORS_ORIGINS: no browser origins (set CORS_ORIGINS for deploy hosts).
        """
        common = {
            "allow_credentials": False,
            "allow_methods": list(_CORS_ALLOW_METHODS),
            "allow_headers": ["*"],
            "allow_origin_regex": None,
        }
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if raw:
            return {
                **common,
                "allow_origins": [o.strip() for o in raw.split(",") if o.strip()],
            }
        if cls._runtime_env_name() == "production":
            return {
                **common,
                "allow_origins": [],
            }
        return {
            **common,
            "allow_origins": [_DEFAULT_DEV_CORS_ORIGIN],
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
