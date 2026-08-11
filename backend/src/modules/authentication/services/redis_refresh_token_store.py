"""Redis-backed refresh token store.

Keys:
  refresh:{sha256(token)}   → session JSON (TTL = refresh lifetime)
  user_refresh:{user_id}    → set of token hashes (for logout-all)

The raw refresh token is never stored — only its SHA-256 digest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis

from src.config.settings import Settings
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.value_objects.refresh_token import RefreshToken


def _token_digest(token: RefreshToken | str) -> str:
    raw = token.value if isinstance(token, RefreshToken) else token
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RedisRefreshTokenStore(RefreshTokenStore):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._ttl_seconds = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

    def _token_key(self, digest: str) -> str:
        return f"refresh:{digest}"

    def _user_key(self, user_id: UUID) -> str:
        return f"user_refresh:{user_id}"

    async def save(self, token: RefreshToken, session: RefreshSessionDto) -> None:
        digest = _token_digest(token)
        payload = json.dumps(
            {
                "user_id": str(session.user_id),
                "email": session.email,
                "full_name": session.full_name,
                "tenant_id": str(session.tenant_id),
                "tenant_slug": session.tenant_slug,
                "role_ids": [str(rid) for rid in session.role_ids],
                "created_at": session.created_at.isoformat(),
            }
        )
        key = self._token_key(digest)
        user_key = self._user_key(session.user_id)
        pipe = self._redis.pipeline()
        pipe.set(key, payload, ex=self._ttl_seconds)
        pipe.sadd(user_key, digest)
        pipe.expire(user_key, self._ttl_seconds)
        await pipe.execute()

    async def get(self, token: RefreshToken) -> RefreshSessionDto | None:
        raw = await self._redis.get(self._token_key(_token_digest(token)))
        if raw is None:
            return None
        data = json.loads(raw)
        return RefreshSessionDto(
            user_id=UUID(data["user_id"]),
            email=data["email"],
            full_name=data["full_name"],
            tenant_id=UUID(data["tenant_id"]),
            tenant_slug=str(data["tenant_slug"]),
            role_ids=tuple(UUID(rid) for rid in data["role_ids"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    async def delete(self, token: RefreshToken) -> None:
        digest = _token_digest(token)
        session = await self.get(token)
        pipe = self._redis.pipeline()
        pipe.delete(self._token_key(digest))
        if session is not None:
            pipe.srem(self._user_key(session.user_id), digest)
        await pipe.execute()

    async def delete_all_for_user(self, user_id: object) -> None:
        uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        user_key = self._user_key(uid)
        digests = await self._redis.smembers(user_key)
        if digests:
            pipe = self._redis.pipeline()
            for digest in digests:
                value = digest.decode() if isinstance(digest, bytes) else str(digest)
                pipe.delete(self._token_key(value))
            pipe.delete(user_key)
            await pipe.execute()
