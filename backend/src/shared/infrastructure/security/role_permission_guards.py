"""Helpers to enforce privilege hierarchy when mutating role permissions."""

from __future__ import annotations

from uuid import UUID

from src.modules.permissions.dtos.permission_dtos import PermissionDto
from src.modules.permissions.queries.permission_queries import GetPermissionsByIdsQuery
from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRoleByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.authorization import HierarchyPolicy
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import get_rls_bypass


async def ensure_can_edit_role_permissions(
    *,
    actor: CurrentUser,
    role_id: UUID,
    permission_ids: frozenset[UUID],
    query_bus: QueryBus,
) -> RoleDto:
    """Actor must outrank the role; platform-only codes require RLS bypass."""
    role: RoleDto = await query_bus.ask(GetRoleByIdQuery(role_id=role_id))
    if not HierarchyPolicy.can_manage(actor.role_names, (role.name,)):
        raise ForbiddenError("Cannot modify permissions on a role with equal or higher privilege")

    if permission_ids and not get_rls_bypass():
        perms: list[PermissionDto] = await query_bus.ask(
            GetPermissionsByIdsQuery(permission_ids=permission_ids)
        )
        forbidden = sorted(
            {
                perm.code
                for perm in perms
                if perm.code in PermissionCode.platform_only_codes()
            }
        )
        if forbidden:
            raise ForbiddenError(
                "Cannot assign platform-only permission(s): " + ", ".join(forbidden)
            )
    return role
