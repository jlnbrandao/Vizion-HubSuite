"""In-memory refresh token store for unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.config.settings import Settings
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.value_objects.refresh_token import RefreshToken


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
        expires_at = datetime.now(UTC) + self._ttl
        self._sessions[token.value] = (session, expires_at)
        self._by_user.setdefault(session.user_id, set()).add(token.value)

    async def get(self, token: RefreshToken) -> RefreshSessionDto | None:
        self._purge_expired()
        entry = self._sessions.get(token.value)
        return entry[0] if entry else None

    async def delete(self, token: RefreshToken) -> None:
        entry = self._sessions.pop(token.value, None)
        if entry:
            self._by_user.get(entry[0].user_id, set()).discard(token.value)

    async def delete_all_for_user(self, user_id: object) -> None:
        uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        tokens = list(self._by_user.get(uid, set()))
        for value in tokens:
            self._sessions.pop(value, None)
        self._by_user.pop(uid, None)
