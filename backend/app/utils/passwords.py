# app/utils/passwords.py
"""Password hashing (bcrypt) with legacy plain-text verification for old documents."""

import bcrypt

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash string suitable for storing in ``password_hash``."""
    if not plain:
        raise ValueError("password must not be empty")
    pw = plain.encode("utf-8")
    if len(pw) > 72:
        pw = pw[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("ascii")


def verify_stored_password(plain: str, stored: str | None) -> bool:
    """
    Verify ``plain`` against ``stored``.

    If ``stored`` looks like a bcrypt hash, use bcrypt. Otherwise compare as plain
    text (legacy demo documents).
    """
    if not plain or stored is None:
        return False
    if isinstance(stored, bytes):
        stored = stored.decode("utf-8")
    if stored.startswith(_BCRYPT_PREFIXES):
        try:
            pw = plain.encode("utf-8")
            if len(pw) > 72:
                pw = pw[:72]
            return bcrypt.checkpw(pw, stored.encode("ascii"))
        except (ValueError, TypeError):
            return False
    return plain == stored
