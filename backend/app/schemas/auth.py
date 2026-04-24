# app/schemas/auth.py
"""Pydantic request bodies for auth routes (validated before service layer)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterBody(BaseModel):
    """POST /api/auth/register — matches frontend `full_name`, `email`, `password`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    # bcrypt uses the first 72 bytes; cap avoids surprising truncation
    password: str = Field(..., min_length=8, max_length=72)


class LoginBody(BaseModel):
    """POST /api/auth/login — email as str so legacy addresses still reach the service."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(..., min_length=1, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)
