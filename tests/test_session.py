"""Tests for the session manager (IN-2)."""
from api_design_standards.session_manager import (
    create_session_token, validate_session_token, is_session_expiring_soon
)


def test_token_roundtrip():
    token = create_session_token("user-1", "demo@example.com")
    payload = validate_session_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["email"] == "demo@example.com"


def test_invalid_token():
    result = validate_session_token("not.a.real.token")
    assert result is None
