"""Tests for the account lockout rate limiter (IN-1)."""
import pytest
from api_design_standards.rate_limiter import (
    record_failed_attempt, is_locked_out,
    reset_attempts, remaining_lockout_seconds,
    LOCKOUT_THRESHOLD,
)


def test_lockout_after_threshold():
    user = "test_lockout@example.com"
    reset_attempts(user)  # clean state
    for _ in range(LOCKOUT_THRESHOLD - 1):
        locked = record_failed_attempt(user)
        assert not locked

    locked = record_failed_attempt(user)
    assert locked
    assert is_locked_out(user)


def test_reset_clears_lockout():
    user = "test_reset@example.com"
    for _ in range(LOCKOUT_THRESHOLD):
        record_failed_attempt(user)
    reset_attempts(user)
    assert not is_locked_out(user)
