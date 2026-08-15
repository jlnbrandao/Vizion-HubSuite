"""Session denylist — makes access-token revocation immediate.

Revoking a session only drops the refresh token, so a stolen access token would
stay usable until it expires. Sessions revoked here are rejected by
`get_current_user` via the `sid` claim.

Key: revoked_session:{session_id} — TTL matches the access-token lifetime, since
after that the token is worthless anyway.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from redis.asyncio import Redis

from src.config.settings import Settings


class SessionDenylist(ABC):
    @abstractmethod
    async def revoke(self, session_id: UUID) -> None: ...

    @abstractmethod
    async def revoke_many(self, session_ids: Iterable[UUID]) -> None: ...

    @abstractmethod
    async def is_revoked(self, session_id: UUID) -> bool: ...


def _key(session_id: UUID) -> str:
    return f"revoked_session:{session_id}"


class RedisSessionDenylist(SessionDenylist):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        # Small skew so a token minted moments before revocation cannot outlive the entry.
        self._ttl_seconds = settings.access_token_ttl_seconds + 60

    async def revoke(self, session_id: UUID) -> None:
        await self._redis.set(_key(session_id), "1", ex=self._ttl_seconds)

    async def revoke_many(self, session_ids: Iterable[UUID]) -> None:
        ids = list(session_ids)
        if not ids:
            return
        pipe = self._redis.pipeline()
        for session_id in ids:
            pipe.set(_key(session_id), "1", ex=self._ttl_seconds)
        await pipe.execute()

    async def is_revoked(self, session_id: UUID) -> bool:
        return bool(await self._redis.exists(_key(session_id)))


class InMemorySessionDenylist(SessionDenylist):
    """Test double — no TTL simulation."""

    def __init__(self) -> None:
        self._revoked: set[UUID] = set()

    async def revoke(self, session_id: UUID) -> None:
        self._revoked.add(session_id)

    async def revoke_many(self, session_ids: Iterable[UUID]) -> None:
        self._revoked.update(session_ids)

    async def is_revoked(self, session_id: UUID) -> bool:
        return session_id in self._revoked

    def clear(self) -> None:
        self._revoked.clear()
