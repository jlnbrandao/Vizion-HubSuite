"""PyJWT access token service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError

from src.config.settings import Settings
from src.modules.authentication.services.token_service import TokenService
from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims
from src.shared.infrastructure.exceptions import UnauthorizedError


class JwtTokenService(TokenService):
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._expire_minutes = settings.jwt_access_token_expire_minutes

    def access_token_expires_in_seconds(self) -> int:
        return self._expire_minutes * 60

    def create_access_token(self, claims: AccessTokenClaims) -> str:
        now = datetime.now(UTC)
        exp = now + timedelta(minutes=self._expire_minutes)
        payload = claims.to_primitive()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int(exp.timestamp())
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["exp", "iat", "sub"]},
            )
        except InvalidTokenError as exc:
            raise UnauthorizedError("Invalid or expired access token") from exc

        try:
            claims = AccessTokenClaims.from_primitive(payload)
        except (KeyError, ValueError, TypeError) as exc:
            raise UnauthorizedError("Invalid access token payload") from exc

        # Refuse tokens minted for another purpose (MFA challenge, OAuth, ...).
        if claims.token_use != "access":
            raise UnauthorizedError("Invalid access token payload")
        return claims
