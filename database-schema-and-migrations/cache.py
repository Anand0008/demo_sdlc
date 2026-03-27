"""
Caching layer to reduce database load and improve API performance.
Related Jira: IN-9 — Add caching to improve performance of slow API endpoints.

Standard: See Confluence > Database Schema and Migrations > Caching Strategy
"""
import functools
import time
import json
import hashlib
import os

try:
    import redis
    _redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        decode_responses=True,
    )
    _redis_available = True
except Exception:
    _redis_available = False

# Fallback in-process cache (for local dev without Redis)
_local_cache: dict[str, tuple[str, float]] = {}

DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))


class cache:
    """
    Decorator factory for caching function results.

    Usage:
        @cache(ttl=60)
        def get_user_profile(user_id: str) -> dict:
            ...
    """
    def __init__(self, ttl: int = DEFAULT_TTL_SECONDS, key_prefix: str = ""):
        self.ttl = ttl
        self.key_prefix = key_prefix

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            raw_key = f"{self.key_prefix}{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            # Try Redis first
            if _redis_available:
                try:
                    cached = _redis_client.get(cache_key)
                    if cached is not None:
                        return json.loads(cached)
                except Exception:
                    pass

            # Fall back to local in-process cache
            if cache_key in _local_cache:
                value, expires_at = _local_cache[cache_key]
                if time.monotonic() < expires_at:
                    return json.loads(value)

            # Cache miss — call the actual function
            result = func(*args, **kwargs)
            serialized = json.dumps(result)

            if _redis_available:
                try:
                    _redis_client.setex(cache_key, self.ttl, serialized)
                except Exception:
                    pass

            _local_cache[cache_key] = (serialized, time.monotonic() + self.ttl)
            return result
        return wrapper


def invalidate(pattern: str) -> int:
    """Invalidate all cache entries matching a key pattern."""
    count = 0
    if _redis_available:
        try:
            keys = _redis_client.keys(pattern)
            if keys:
                count = _redis_client.delete(*keys)
        except Exception:
            pass
    return count
