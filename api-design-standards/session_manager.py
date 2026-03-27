"""
Session duration management.
Related Jira: IN-2 — Extend user session from 15 minutes to 30 days.

Standard: See Confluence > API Design Standards > Session Management
"""
import jwt
import os
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
SESSION_DURATION_DAYS = int(os.getenv("SESSION_DURATION_DAYS", "30"))


def create_session_token(user_id: str, email: str) -> str:
    """
    Generate a JWT session token valid for SESSION_DURATION_DAYS.
    Extended from the original 15-minute expiry (IN-2).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=SESSION_DURATION_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def validate_session_token(token: str) -> dict | None:
    """
    Validate a JWT session token and return its payload.
    Returns None if token is invalid or expired.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def is_session_expiring_soon(token: str, threshold_hours: int = 24) -> bool:
    """
    Returns True if the session expires within `threshold_hours`.
    Used to proactively prompt the user to re-authenticate.
    """
    payload = validate_session_token(token)
    if not payload:
        return True
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    remaining = exp - datetime.now(timezone.utc)
    return remaining < timedelta(hours=threshold_hours)
