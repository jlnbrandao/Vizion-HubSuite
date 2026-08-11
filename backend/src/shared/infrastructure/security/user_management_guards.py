"""Helpers to enforce privilege hierarchy when managing users."""

from __future__ import annotations

from uuid import UUID

from src.modules.authentication.queries.access_queries import (
    EffectiveAccessDto,
    ResolveEffectiveAccessQuery,
)
from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRolesByIdsQuery
from src.modules.users.dtos.user_dtos import UserDto
from src.modules.users.queries.user_queries import GetUserByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.role_hierarchy import can_grant_roles, can_manage


async def _role_names_for_ids(query_bus: QueryBus, role_ids: frozenset[UUID]) -> frozenset[str]:
    if not role_ids:
        return frozenset()
    access: EffectiveAccessDto = await query_bus.ask(
        ResolveEffectiveAccessQuery(role_ids=role_ids)
    )
    return access.role_names


async def ensure_can_manage_user(
    *,
    actor: CurrentUser,
    target_user_id: UUID,
    query_bus: QueryBus,
    allow_self: bool = False,
) -> UserDto:
    user: UserDto = await query_bus.ask(GetUserByIdQuery(user_id=target_user_id))
    if allow_self and actor.id == target_user_id:
        return user

    target_roles = await _role_names_for_ids(query_bus, frozenset(user.role_ids))
    if not can_manage(actor.role_names, target_roles):
        raise ForbiddenError("Cannot manage a user with equal or higher privilege")
    return user


async def ensure_can_grant_roles(
    *,
    actor: CurrentUser,
    role_ids: frozenset[UUID],
    query_bus: QueryBus,
) -> None:
    if not role_ids:
        return
    roles: list[RoleDto] = await query_bus.ask(GetRolesByIdsQuery(role_ids=role_ids))
    found_ids = {role.id for role in roles}
    # Inactive / missing roles are rejected elsewhere; still block by name when present.
    names = frozenset(role.name for role in roles)
    if found_ids != set(role_ids):
        # Let the command handler surface unknown IDs; hierarchy only checks known roles.
        pass
    if names and not can_grant_roles(actor.role_names, names):
        raise ForbiddenError("Cannot assign a role with equal or higher privilege")
