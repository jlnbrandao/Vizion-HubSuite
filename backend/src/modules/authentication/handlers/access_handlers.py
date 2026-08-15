"""Resolves role names and permission codes from role IDs via QueryBus.

Does not import Roles/Permissions domain — only public queries/DTOs.
"""

from __future__ import annotations

from uuid import UUID

from src.modules.authentication.queries.access_queries import (
    EffectiveAccessDto,
    ResolveEffectiveAccessQuery,
)
from src.modules.permissions.dtos.permission_dtos import PermissionDto
from src.modules.permissions.queries.permission_group_queries import (
    ResolveRoleBundleCodesQuery,
)
from src.modules.permissions.queries.permission_queries import GetPermissionsByIdsQuery
from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRolesByIdsQuery
from src.shared.application.handler import QueryHandler
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.permission_codes import PermissionCode


class ResolveEffectiveAccessHandler(
    QueryHandler[ResolveEffectiveAccessQuery, EffectiveAccessDto]
):
    def __init__(self, query_bus: QueryBus) -> None:
        self._query_bus = query_bus

    async def handle(self, query: ResolveEffectiveAccessQuery) -> EffectiveAccessDto:
        if not query.role_ids:
            return EffectiveAccessDto()

        roles: list[RoleDto] = await self._query_bus.ask(
            GetRolesByIdsQuery(role_ids=query.role_ids)
        )
        role_names = frozenset(role.name for role in roles)

        permission_ids: set[UUID] = set()
        for role in roles:
            permission_ids.update(role.permission_ids)

        codes: set[str] = set()
        if permission_ids:
            permissions: list[PermissionDto] = await self._query_bus.ask(
                GetPermissionsByIdsQuery(permission_ids=frozenset(permission_ids))
            )
            codes.update(permission.code for permission in permissions)

        # Roles also inherit codes from the bundles they compose.
        bundle_codes: frozenset[str] = await self._query_bus.ask(
            ResolveRoleBundleCodesQuery(role_ids=query.role_ids)
        )
        codes.update(bundle_codes)

        if not codes:
            return EffectiveAccessDto(role_names=role_names)

        # Both the namespaced code and its legacy alias authorize during migration.
        return EffectiveAccessDto(
            role_names=role_names,
            permission_codes=PermissionCode.expand(frozenset(codes)),
        )
