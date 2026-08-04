"""Redis client factory.

Used later for refresh-token storage, rate limiting, and optional event bridging.
"""

from redis.asyncio import Redis


def create_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
