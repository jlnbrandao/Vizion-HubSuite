"""TokenService port — create and decode access JWTs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, claims: AccessTokenClaims) -> str:
        ...

    @abstractmethod
    def decode_access_token(self, token: str) -> AccessTokenClaims:
        """Raise UnauthorizedError if invalid or expired."""

    @abstractmethod
    def access_token_expires_in_seconds(self) -> int:
        ...
