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
from src.modules.users.dtos.user_dtos import UserDto
from src.modules.users.queries.user_queries import GetUserByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import (
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.tenant_context import (
    get_current_tenant_id,
    get_current_tenant_name,
    get_current_tenant_slug,
)

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

    host_tenant_id = get_current_tenant_id()
    if host_tenant_id is None or claims.tenant_id != host_tenant_id:
        raise UnauthorizedError("Token tenant does not match Host tenant")

    host_slug = get_current_tenant_slug()
    if host_slug is not None and claims.tenant_slug != host_slug:
        raise UnauthorizedError("Token tenant does not match Host tenant")

    try:
        user: UserDto = await query_bus.ask(GetUserByIdQuery(user_id=claims.user_id))
    except NotFoundError as exc:
        raise UnauthorizedError("Invalid or expired credentials") from exc

    if not user.is_active or user.tenant_id != host_tenant_id:
        raise UnauthorizedError("Invalid or expired credentials")

    access: EffectiveAccessDto = await query_bus.ask(
        ResolveEffectiveAccessQuery(role_ids=frozenset(user.role_ids))
    )

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        tenant_slug=claims.tenant_slug,
        tenant_name=get_current_tenant_name() or claims.tenant_slug,
        role_ids=user.role_ids,
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
