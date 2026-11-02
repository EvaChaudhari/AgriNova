"""In-Memory Sliding-Window Rate Limiter & Token Revocation Blacklist.

Protects sensitive authentication, chat, and sync endpoints from volumetric flooding
and credential stuffing, and tracks revoked JWT access tokens.
"""

from collections import defaultdict
import time
from typing import Callable, Optional
from fastapi import Request

from app.core.exceptions import RateLimitExceededError


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter maintaining high-resolution timestamps per key."""

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """Check if request rate limit is exceeded for the key.

        Returns:
            tuple[bool, int]: (is_limited, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds
        records = self._history[key]

        # Prune expired timestamps
        self._history[key] = [t for t in records if t > window_start]
        records = self._history[key]

        if len(records) >= max_requests:
            oldest_in_window = records[0]
            retry_after = int(window_seconds - (now - oldest_in_window)) + 1
            return True, max(1, retry_after)

        records.append(now)
        return False, 0

    def reset(self) -> None:
        """Clear all rate limit history."""
        self._history.clear()


# Global in-memory rate limiter instance
global_rate_limiter = SlidingWindowRateLimiter()

# In-memory token blacklist store
_revoked_tokens: set[str] = set()


def blacklist_token(token: str) -> None:
    """Add a JWT token to the revoked blacklist."""
    cleaned = token.strip()
    if cleaned.startswith("Bearer "):
        cleaned = cleaned[7:].strip()
    _revoked_tokens.add(cleaned)


def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT token has been revoked."""
    cleaned = token.strip()
    if cleaned.startswith("Bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned in _revoked_tokens


def clear_token_blacklist() -> None:
    """Clear all revoked tokens (used for testing)."""
    _revoked_tokens.clear()


def rate_limit(max_requests: int, window_seconds: int) -> Callable:
    """FastAPI dependency factory enforcing rate limits on endpoints."""

    async def _rate_limiter_dependency(request: Request) -> None:
        # Resolve client identifier from Forwarded-For or client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        endpoint_path = request.url.path
        key = f"{client_ip}:{endpoint_path}"

        is_limited, retry_after = global_rate_limiter.is_rate_limited(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if is_limited:
            raise RateLimitExceededError(
                detail=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s. Try again in {retry_after} seconds.",
                retry_after=retry_after,
            )

    return _rate_limiter_dependency

