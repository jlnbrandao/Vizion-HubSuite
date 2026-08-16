from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from openvizion.kernel.identity import Principal

from tracking.domain.errors import UnauthorizedError
from tracking.permissions import ADMIN_PERMISSIONS, OPERATOR_PERMISSIONS, VIEWER_PERMISSIONS

_ROLE_PERMISSIONS = {
    "ADMIN": ADMIN_PERMISSIONS,
    "OPERATOR": OPERATOR_PERMISSIONS,
    "VIEWER": VIEWER_PERMISSIONS,
}


class JwtService:
    def __init__(self, secret: str, algorithm: str = "HS256", expire_minutes: int = 30) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, principal: Principal) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(principal.id),
            "email": principal.email,
            "full_name": principal.full_name,
            "tenant_id": str(principal.tenant_id),
            "tenant_slug": principal.tenant_slug,
            "tenant_name": principal.tenant_name,
            "roles": sorted(principal.role_names),
            "permissions": sorted(principal.permissions),
            "token_use": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._expire_minutes)).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> Principal:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except InvalidTokenError as exc:
            raise UnauthorizedError("Invalid or expired access token") from exc
        if payload.get("token_use") != "access":
            raise UnauthorizedError("Invalid access token payload")
        return Principal(
            id=UUID(payload["sub"]),
            email=payload["email"],
            full_name=payload["full_name"],
            tenant_id=UUID(payload["tenant_id"]),
            tenant_slug=payload["tenant_slug"],
            tenant_name=payload.get("tenant_name") or "",
            role_names=frozenset(payload.get("roles") or []),
            permissions=frozenset(payload.get("permissions") or []),
        )


def permissions_for_role(role_name: str) -> frozenset[str]:
    return _ROLE_PERMISSIONS.get(role_name.upper(), VIEWER_PERMISSIONS)
