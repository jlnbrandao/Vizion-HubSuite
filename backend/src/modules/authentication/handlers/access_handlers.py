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
from src.modules.permissions.queries.permission_queries import GetPermissionsByIdsQuery
from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRolesByIdsQuery
from src.shared.application.handler import QueryHandler
from src.shared.application.query_bus import QueryBus


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

        if not permission_ids:
            return EffectiveAccessDto(role_names=role_names)

        permissions: list[PermissionDto] = await self._query_bus.ask(
            GetPermissionsByIdsQuery(permission_ids=frozenset(permission_ids))
        )
        codes = frozenset(permission.code for permission in permissions)
        return EffectiveAccessDto(role_names=role_names, permission_codes=codes)
