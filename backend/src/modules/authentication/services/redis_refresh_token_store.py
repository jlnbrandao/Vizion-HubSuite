"""Redis-backed refresh token store.

Keys:
  refresh:{token}           → session JSON (TTL = refresh lifetime)
  user_refresh:{user_id}    → set of refresh tokens (for logout-all)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from redis.asyncio import Redis

from src.config.settings import Settings
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.value_objects.refresh_token import RefreshToken


class RedisRefreshTokenStore(RefreshTokenStore):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._ttl_seconds = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

    def _token_key(self, token: RefreshToken) -> str:
        return f"refresh:{token.value}"

    def _user_key(self, user_id: UUID) -> str:
        return f"user_refresh:{user_id}"

    async def save(self, token: RefreshToken, session: RefreshSessionDto) -> None:
        payload = json.dumps(
            {
                "user_id": str(session.user_id),
                "email": session.email,
                "full_name": session.full_name,
                "role_ids": [str(rid) for rid in session.role_ids],
                "created_at": session.created_at.isoformat(),
            }
        )
        key = self._token_key(token)
        user_key = self._user_key(session.user_id)
        pipe = self._redis.pipeline()
        pipe.set(key, payload, ex=self._ttl_seconds)
        pipe.sadd(user_key, token.value)
        pipe.expire(user_key, self._ttl_seconds)
        await pipe.execute()

    async def get(self, token: RefreshToken) -> RefreshSessionDto | None:
        raw = await self._redis.get(self._token_key(token))
        if raw is None:
            return None
        data = json.loads(raw)
        return RefreshSessionDto(
            user_id=UUID(data["user_id"]),
            email=data["email"],
            full_name=data["full_name"],
            role_ids=tuple(UUID(rid) for rid in data["role_ids"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    async def delete(self, token: RefreshToken) -> None:
        session = await self.get(token)
        pipe = self._redis.pipeline()
        pipe.delete(self._token_key(token))
        if session is not None:
            pipe.srem(self._user_key(session.user_id), token.value)
        await pipe.execute()

    async def delete_all_for_user(self, user_id: object) -> None:
        uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        user_key = self._user_key(uid)
        tokens = await self._redis.smembers(user_key)
        if tokens:
            pipe = self._redis.pipeline()
            for value in tokens:
                pipe.delete(f"refresh:{value}")
            pipe.delete(user_key)
            await pipe.execute()
