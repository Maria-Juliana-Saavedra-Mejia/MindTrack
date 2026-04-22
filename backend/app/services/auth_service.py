# app/services/auth_service.py
"""Authentication and user lookup."""

from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId

from app.models.user import User
from app.utils.error_handlers import InvalidCredentialsError, UserAlreadyExistsError


class AuthService:
    """Handles registration, login, and user retrieval."""

    def __init__(self, db, jwt_secret, jwt_expiry_hours):
        self._users = db["users"]
        self._jwt_secret = jwt_secret
        self._jwt_expiry_hours = jwt_expiry_hours

    def register_user(self, data):
        """Create a new user document."""
        full_name = (data or {}).get("full_name", "").strip()
        email = (data or {}).get("email", "").strip().lower()
        password = (data or {}).get("password", "")
        if not full_name or not email or not password:
            raise ValueError("full_name, email, and password are required")
        if self._users.find_one({"email": email}):
            raise UserAlreadyExistsError("Email already registered")
        user = User(full_name=full_name, email=email, password=password)
        doc = user.to_dict(include_hash=True)
        doc["email"] = user.email
        doc["full_name"] = user.full_name
        result = self._users.insert_one(doc)
        created = self._users.find_one({"_id": result.inserted_id})
        return self._serialize_user(created)

    def login_user(self, email, password):
        """Authenticate user and return token payload."""
        if not email or not password:
            raise InvalidCredentialsError("Invalid email or password")
        doc = self._users.find_one({"email": email.strip().lower()})
        if not doc:
            raise InvalidCredentialsError("Invalid email or password")
        user = User.from_dict(doc)
        if not user.verify_password(password):
            raise InvalidCredentialsError("Invalid email or password")
        now = datetime.now(timezone.utc)
        self._users.update_one(
            {"_id": doc["_id"]}, {"$set": {"last_login": now}}
        )
        token = self._issue_token(str(doc["_id"]))
        return {"access_token": token, "user": self._serialize_user(doc)}

    def get_user_by_id(self, user_id):
        """Return a user dict without sensitive fields."""
        oid = self._to_object_id(user_id)
        doc = self._users.find_one({"_id": oid})
        if not doc:
            raise InvalidCredentialsError("User not found")
        return self._serialize_user(doc)

    def _issue_token(self, user_id: str):
        exp = datetime.now(timezone.utc) + timedelta(hours=self._jwt_expiry_hours)
        payload = {"sub": user_id, "exp": exp}
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")

    @staticmethod
    def _serialize_user(doc):
        return {
            "id": str(doc["_id"]),
            "full_name": doc.get("full_name"),
            "email": doc.get("email"),
            "preferences": doc.get("preferences", {}),
            "created_at": doc.get("created_at").isoformat()
            if doc.get("created_at")
            else None,
            "last_login": doc.get("last_login").isoformat()
            if doc.get("last_login")
            else None,
        }

    @staticmethod
    def _to_object_id(user_id):
        try:
            return ObjectId(str(user_id))
        except Exception as exc:
            raise InvalidCredentialsError("Invalid user id") from exc
