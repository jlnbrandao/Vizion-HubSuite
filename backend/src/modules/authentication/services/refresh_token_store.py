"""RefreshTokenStore port — persist opaque refresh tokens (Redis in prod)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto
from src.modules.authentication.value_objects.refresh_token import RefreshToken


class RefreshTokenStore(ABC):
    @abstractmethod
    async def save(self, token: RefreshToken, session: RefreshSessionDto) -> None:
        ...

    @abstractmethod
    async def get(self, token: RefreshToken) -> RefreshSessionDto | None:
        ...

    @abstractmethod
    async def delete(self, token: RefreshToken) -> None:
        ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: object) -> None:
        """Optional bulk revoke (logout-all)."""
