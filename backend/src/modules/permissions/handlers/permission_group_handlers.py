"""Query handlers for permission bundles."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from src.modules.permissions.groups.service import PermissionGroupService
from src.modules.permissions.queries.permission_group_queries import (
    ResolveRoleBundleCodesQuery,
)
from src.shared.application.handler import QueryHandler
from src.shared.application.unit_of_work import UnitOfWork

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


class ResolveRoleBundleCodesHandler(
    QueryHandler[ResolveRoleBundleCodesQuery, frozenset[str]]
):
    def __init__(self, uow_factory: UowFactory, groups: PermissionGroupService) -> None:
        self._uow_factory = uow_factory
        self._groups = groups

    async def handle(self, query: ResolveRoleBundleCodesQuery) -> frozenset[str]:
        if not query.role_ids:
            return frozenset()
        async with self._uow_factory():
            return await self._groups.codes_for_roles(query.role_ids)
