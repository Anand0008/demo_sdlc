"""
Account lockout after consecutive failed login attempts.
Related Jira: IN-1 — Lock user account for 15 minutes after 5 consecutive
failed login attempts.

Standard: See Confluence > API Design Standards > Authentication
"""
import time
from collections import defaultdict
from threading import Lock

LOCKOUT_THRESHOLD = 5       # failed attempts before lockout
LOCKOUT_DURATION_SEC = 900  # 15 minutes

_attempts: dict[str, list[float]] = defaultdict(list)
_lockouts: dict[str, float] = {}
_lock = Lock()


def record_failed_attempt(username: str) -> bool:
    """
    Record a failed login attempt for a user.
    Returns True if the account is now locked out.
    """
    now = time.monotonic()
    with _lock:
        # Remove attempts older than the lockout window
        _attempts[username] = [
            t for t in _attempts[username]
            if now - t < LOCKOUT_DURATION_SEC
        ]
        _attempts[username].append(now)

        if len(_attempts[username]) >= LOCKOUT_THRESHOLD:
            _lockouts[username] = now
            _attempts[username] = []
            return True
    return False


def is_locked_out(username: str) -> bool:
    """Check if a user account is currently locked out."""
    lockout_time = _lockouts.get(username)
    if lockout_time is None:
        return False
    if time.monotonic() - lockout_time >= LOCKOUT_DURATION_SEC:
        del _lockouts[username]
        return False
    return True


def remaining_lockout_seconds(username: str) -> int:
    """Returns seconds remaining in lockout, 0 if not locked."""
    lockout_time = _lockouts.get(username)
    if lockout_time is None:
        return 0
    elapsed = time.monotonic() - lockout_time
    remaining = LOCKOUT_DURATION_SEC - elapsed
    return max(0, int(remaining))


def reset_attempts(username: str) -> None:
    """Clear failed attempt history on successful login."""
    with _lock:
        _attempts.pop(username, None)
        _lockouts.pop(username, None)
