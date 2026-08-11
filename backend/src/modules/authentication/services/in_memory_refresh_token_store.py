"""In-memory refresh token store for unit tests (stores SHA-256 digests only)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.config.settings import Settings
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.value_objects.refresh_token import RefreshToken


def _token_digest(token: RefreshToken | str) -> str:
    raw = token.value if isinstance(token, RefreshToken) else token
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InMemoryRefreshTokenStore(RefreshTokenStore):
    def __init__(self, settings: Settings | None = None) -> None:
        self._ttl = timedelta(
            days=(settings.jwt_refresh_token_expire_days if settings else 7)
        )
        self._sessions: dict[str, tuple[RefreshSessionDto, datetime]] = {}
        self._by_user: dict[UUID, set[str]] = {}

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        expired = [k for k, (_, exp) in self._sessions.items() if exp <= now]
        for key in expired:
            session, _ = self._sessions.pop(key)
            self._by_user.get(session.user_id, set()).discard(key)

    async def save(self, token: RefreshToken, session: RefreshSessionDto) -> None:
        self._purge_expired()
        digest = _token_digest(token)
        expires_at = datetime.now(UTC) + self._ttl
        self._sessions[digest] = (session, expires_at)
        self._by_user.setdefault(session.user_id, set()).add(digest)

    async def get(self, token: RefreshToken) -> RefreshSessionDto | None:
        self._purge_expired()
        entry = self._sessions.get(_token_digest(token))
        return entry[0] if entry else None

    async def delete(self, token: RefreshToken) -> None:
        digest = _token_digest(token)
        entry = self._sessions.pop(digest, None)
        if entry:
            self._by_user.get(entry[0].user_id, set()).discard(digest)

    async def delete_all_for_user(self, user_id: object) -> None:
        uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        digests = list(self._by_user.get(uid, set()))
        for digest in digests:
            self._sessions.pop(digest, None)
        self._by_user.pop(uid, None)
