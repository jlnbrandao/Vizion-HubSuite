"""Helpers to enforce privilege hierarchy when creating / mutating roles."""

from __future__ import annotations

from uuid import UUID

from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRoleByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.role_hierarchy import can_grant_roles, can_manage


def ensure_can_create_role_name(*, actor: CurrentUser, name: str) -> None:
    """Actor must strictly outrank the role name (blocks peer ADMIN / PLATFORM)."""
    if not can_grant_roles(actor.role_names, (name,)):
        raise ForbiddenError("Cannot create a role with equal or higher privilege")


async def ensure_can_manage_role(
    *,
    actor: CurrentUser,
    role_id: UUID,
    query_bus: QueryBus,
) -> RoleDto:
    """Actor must outrank the target role before update / delete."""
    role: RoleDto = await query_bus.ask(GetRoleByIdQuery(role_id=role_id))
    if not can_manage(actor.role_names, (role.name,)):
        raise ForbiddenError("Cannot manage a role with equal or higher privilege")
    return role
