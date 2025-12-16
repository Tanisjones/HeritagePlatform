from __future__ import annotations

import time

from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import APIException


class AIRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "ai_rate_limited"
    default_detail = "Too many AI requests. Please try again shortly."


def enforce_user_rate_limit(*, user_id: int, operation: str, limit_per_minute: int = 10) -> None:
    """
    Very small, cache-based rate limiter. Uses the default Django cache backend.
    """
    bucket = int(time.time() // 60)
    key = f"ai_rl:{user_id}:{operation}:{bucket}"

    # Ensure key exists with TTL so bucket naturally expires.
    cache.add(key, 0, timeout=70)
    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=70)
        current = 1

    if current > limit_per_minute:
        raise AIRateLimited()

