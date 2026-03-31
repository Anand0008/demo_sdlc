## IN-1: Lock user account for 15 minutes after 5 consecutive failed login attempts

**Jira Ticket:** [IN-1](https://anandinfinity0007.atlassian.net/browse/IN-1)

## Summary
Implement login attempt protection with Redis-backed account lockout mechanism

## Implementation Plan

**Step 1: Create LoginGuard Redis Connection**  
Set up Redis connection in login_guard.py with fail-open error handling. Use environment-based configuration for Redis host and port.
Files: `auth/login_guard.py`

**Step 2: Implement record_failure Method**  
Create method to increment Redis counter for username with 900s TTL. Use atomic Redis operations to ensure thread-safety.
Files: `auth/login_guard.py`

**Step 3: Implement is_locked Method**  
Create method to check if login attempts exceed 5, returning (is_locked, remaining_ttl). Handle Redis connection errors with fail-open logic.
Files: `auth/login_guard.py`

**Step 4: Implement reset Method**  
Create method to delete Redis key on successful login, clearing failure counter.
Files: `auth/login_guard.py`

**Step 5: Modify JWT Login Endpoint**  
Update jwt_handler.py to call LoginGuard.is_locked() before password validation. Return HTTP 423 with retry_after_seconds if locked.
Files: `auth/jwt_handler.py`

**Step 6: Implement Unit Tests**  
Create comprehensive test cases in test_login_guard.py covering lockout scenarios, reset behavior, and Redis failure modes.
Files: `tests/test_login_guard.py`

**Risk Level:** MEDIUM — Medium risk due to security-critical feature involving authentication logic and external Redis dependency. Potential for introducing authentication bypass or incorrect lockout behavior.

**Deployment Notes:**
- Ensure Redis is configured and accessible in target environment
- Verify Redis connection parameters are correctly set in environment variables
- Update monitoring to track login lockout events
- Communicate new login protection mechanism to support team

## Proposed Code Changes

### `auth/login_guard.py` (create)
Implement LoginGuard class with Redis-backed login attempt tracking, supporting the requirements of tracking failed login attempts, locking accounts, and providing fail-open behavior.
```python
import os
import redis
import logging
from typing import Tuple

class LoginGuard:
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True
            )
        except redis.ConnectionError:
            logging.warning('Redis connection failed. Login attempts will proceed normally.')
            self.redis_client = None

    def _get_failure_key(self, username: str) -> str:
        return f'login:fail:{username}'

    def record_failure(self, username: str) -> None:
        if not self.redis_client:
            return

        try:
            key = self._get_failure_key(username)
            # Increment counter and set 15-minute expiry
            self.redis_client.incr(key)
            self.redis_client.expire(key, 900)
        except redis.RedisError:
            logging.warning(f'Failed to record login failure for {username}')

    def is_locked(self, username: str) -> Tuple[bool, int]:
        if not self.redis_client:
            return False, 0

        try:
            key = self._get_failure_key(username)
            failure_count = int(self.redis_client.get(key) or 0)
            
            if failure_count >= 5:
                # Return remaining TTL in seconds
                remaining_ttl = self.redis_client.ttl(key)
                return True, max(remaining_ttl, 0)
            
            return False, 0
        except redis.RedisError:
            logging.warning(f'Failed to check lock status for {username}')
            return False, 0

    def reset(self, username: str) -> None:
        if not self.redis_client:
            return

        try:
            key = self._get_failure_key(username)
            self.redis_client.delete(key)
        except redis.RedisError:
            logging.warning(f'Failed to reset login failures for {username}')
```

### `auth/jwt_handler.py` (modify)
Modify login endpoint to integrate with LoginGuard, checking account lock status before password validation, recording failures, and resetting on successful login.
```python
--- a/auth/jwt_handler.py
+++ b/auth/jwt_handler.py
@@ -1,8 +1,12 @@
 from flask import jsonify, make_response
 from werkzeug.security import check_password_hash
+from auth.login_guard import LoginGuard
 
 def login(username, password):
+    login_guard = LoginGuard()
+    
     # Check if account is locked first
+    is_locked, retry_after = login_guard.is_locked(username)
+    if is_locked:
+        return make_response(jsonify({
+            'error': 'account_locked', 
+            'retry_after_seconds': retry_after
+        }), 423)
     
     # Validate password
     user = get_user(username)
     if user and check_password_hash(user.password, password):
+        login_guard.reset(username)  # Reset failure count on successful login
         return create_jwt_token(user)
     else:
+        login_guard.record_failure(username)  # Record login failure
         return make_response(jsonify({'error': 'Invalid credentials'}), 401)
```

**New Dependencies:**
- `redis`

## Test Suggestions

Framework: `pytest`

- **test_login_guard_tracks_consecutive_failed_attempts** — Verify that failed login attempts are correctly tracked
- **test_account_locks_after_fifth_failed_attempt** *(edge case)* — Ensure account is locked after 5 consecutive failed attempts
- **test_login_blocked_with_http_423_on_sixth_attempt** — Verify HTTP 423 is returned on 6th login attempt when locked
- **test_successful_login_resets_failure_counter** — Verify failed attempts are reset after successful login
- **test_account_unlocks_after_fifteen_minutes** *(edge case)* — Ensure account is automatically unlocked after 15 minutes
- **test_login_proceeds_when_redis_is_unavailable** *(edge case)* — Verify login proceeds normally if Redis is down

## Confluence Documentation References

- [Security and Authentication Guidelines](https://anandinfinity0007.atlassian.net/wiki/spaces/SD/pages/1507329) — Provides context for authentication mechanisms and security standards relevant to the login protection implementation
- [API Design Standards](https://anandinfinity0007.atlassian.net/wiki/spaces/SD/pages/1474561) — Provides guidance on rate limiting and abuse prevention, which aligns with the ticket's goal of preventing brute-force login attacks

**Suggested Documentation Updates:**

- Security and Authentication Guidelines
- API Design Standards

## AI Confidence Scores
Plan: 85%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._