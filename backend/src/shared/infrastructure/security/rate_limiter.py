"""Rate limiting — Redis fixed window by client IP."""

from __future__ import annotations

from abc import ABC, abstractmethod

from redis.asyncio import Redis

from src.config.settings import Settings


class RateLimiter(ABC):
    @abstractmethod
    async def is_allowed(self, key: str) -> tuple[bool, int]:
        """Return (allowed, remaining). remaining is -1 when unlimited."""


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._limit = settings.rate_limit_requests
        self._window = settings.rate_limit_window_seconds

    async def is_allowed(self, key: str) -> tuple[bool, int]:
        redis_key = f"rate:{key}"
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, self._window)
        remaining = max(self._limit - count, 0)
        return count <= self._limit, remaining


class InMemoryRateLimiter(RateLimiter):
    """Test double — simple counter without TTL simulation beyond reset helper."""

    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._counts: dict[str, int] = {}

    async def is_allowed(self, key: str) -> tuple[bool, int]:
        self._counts[key] = self._counts.get(key, 0) + 1
        count = self._counts[key]
        remaining = max(self._limit - count, 0)
        return count <= self._limit, remaining

    def reset(self) -> None:
        self._counts.clear()
