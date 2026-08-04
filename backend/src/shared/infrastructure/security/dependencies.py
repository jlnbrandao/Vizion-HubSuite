"""FastAPI AuthN / AuthZ dependencies.

Usage:
  user: CurrentUser = Depends(get_current_user)
  user: CurrentUser = Depends(require_permission(PermissionCode.USERS_CREATE))
  user: CurrentUser = Depends(require_any_role("ADMIN", "MANAGER"))
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Header

from src.modules.authentication.queries.access_queries import (
    EffectiveAccessDto,
    ResolveEffectiveAccessQuery,
)
from src.modules.authentication.services.token_service import TokenService
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import ForbiddenError, UnauthorizedError
from src.shared.infrastructure.security.current_user import CurrentUser

AuthDependency = Callable[..., Coroutine[Any, Any, CurrentUser]]


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Invalid Authorization header")
    return token.strip()


@inject
async def get_current_user(
    authorization: str | None = Header(default=None),
    token_service: TokenService = Depends(Provide[Container.token_service]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> CurrentUser:
    token = _extract_bearer(authorization)
    claims = token_service.decode_access_token(token)

    access: EffectiveAccessDto = await query_bus.ask(
        ResolveEffectiveAccessQuery(role_ids=frozenset(claims.role_ids))
    )

    return CurrentUser(
        id=claims.user_id,
        email=claims.email,
        full_name=claims.full_name,
        role_ids=claims.role_ids,
        role_names=access.role_names,
        permissions=access.permission_codes,
    )


def require_permission(*codes: str) -> AuthDependency:
    """Require ALL listed permission codes."""

    if not codes:
        raise ValueError("require_permission needs at least one code")

    async def _dependency(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_all_permissions(*codes):
            missing = ", ".join(c for c in codes if not user.has_permission(c))
            raise ForbiddenError(f"Missing permission(s): {missing}")
        return user

    return _dependency


def require_any_permission(*codes: str) -> AuthDependency:
    """Require at least ONE of the listed permission codes."""

    if not codes:
        raise ValueError("require_any_permission needs at least one code")

    async def _dependency(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_any_permission(*codes):
            raise ForbiddenError(
                f"Requires one of permissions: {', '.join(codes)}"
            )
        return user

    return _dependency


def require_any_role(*role_names: str) -> AuthDependency:
    """Require at least ONE of the listed role names (e.g. ADMIN)."""

    if not role_names:
        raise ValueError("require_any_role needs at least one role")

    async def _dependency(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_any_role(*role_names):
            raise ForbiddenError(
                f"Requires one of roles: {', '.join(r.upper() for r in role_names)}"
            )
        return user

    return _dependency
