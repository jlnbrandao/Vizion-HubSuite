"""Unit tests for ResolveEffectiveAccessHandler (cross-module AuthZ resolution)."""

from __future__ import annotations

import pytest

from src.modules.authentication.handlers.access_handlers import ResolveEffectiveAccessHandler
from src.modules.authentication.queries.access_queries import ResolveEffectiveAccessQuery
from src.modules.permissions.commands.permission_commands import CreatePermissionCommand
from src.modules.permissions.handlers.permission_handlers import (
    CheckPermissionsExistHandler,
    CreatePermissionHandler,
    GetPermissionsByIdsHandler,
)
from src.modules.permissions.queries.permission_group_queries import (
    ResolveRoleBundleCodesQuery,
)
from src.modules.permissions.queries.permission_queries import (
    CheckPermissionsExistQuery,
    GetPermissionsByIdsQuery,
)
from src.modules.permissions.repositories.in_memory_permission_repository import (
    InMemoryPermissionRepository,
)
from src.modules.roles.commands.role_commands import (
    AssignPermissionsToRoleCommand,
    CreateRoleCommand,
)
from src.modules.roles.handlers.role_handlers import (
    AssignPermissionsToRoleHandler,
    CheckRolesExistHandler,
    CreateRoleHandler,
    GetRolesByIdsHandler,
)
from src.modules.roles.queries.role_queries import CheckRolesExistQuery, GetRolesByIdsQuery
from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.permission_codes import PermissionCode
from tests.unit.conftest import UNIVERSE_TENANT_ID
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


class _NoBundlesHandler:
    async def handle(self, query: ResolveRoleBundleCodesQuery) -> frozenset[str]:
        return frozenset()


@pytest.fixture
def uow_factory():
    bus = EventBus()

    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(bus)

    return factory


@pytest.mark.asyncio
async def test_resolve_effective_access_aggregates_permissions(uow_factory) -> None:
    permissions_repo = InMemoryPermissionRepository()
    roles_repo = InMemoryRoleRepository()
    query_bus = QueryBus()

    query_bus.register(
        CheckPermissionsExistQuery,
        CheckPermissionsExistHandler(uow_factory, permissions_repo),
    )
    query_bus.register(
        GetPermissionsByIdsQuery,
        GetPermissionsByIdsHandler(uow_factory, permissions_repo),
    )
    query_bus.register(
        CheckRolesExistQuery,
        CheckRolesExistHandler(uow_factory, roles_repo),
    )
    query_bus.register(
        GetRolesByIdsQuery,
        GetRolesByIdsHandler(uow_factory, roles_repo),
    )
    # No bundle store in unit scope: roles inherit nothing from bundles here.
    query_bus.register(ResolveRoleBundleCodesQuery, _NoBundlesHandler())

    create_perm = CreatePermissionHandler(uow_factory, permissions_repo)
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    assign = AssignPermissionsToRoleHandler(uow_factory, roles_repo, query_bus)
    resolve = ResolveEffectiveAccessHandler(query_bus)

    p_read = await create_perm.handle(
        CreatePermissionCommand(
            tenant_id=UNIVERSE_TENANT_ID,
            code=PermissionCode.USERS_READ,
            name="Read Users",
        )
    )
    p_create = await create_perm.handle(
        CreatePermissionCommand(
            tenant_id=UNIVERSE_TENANT_ID,
            code=PermissionCode.USERS_CREATE,
            name="Create Users",
        )
    )
    role_id = await create_role.handle(
        CreateRoleCommand(tenant_id=UNIVERSE_TENANT_ID, name="ADMIN")
    )
    await assign.handle(
        AssignPermissionsToRoleCommand(
            role_id=role_id, permission_ids=frozenset({p_read, p_create})
        )
    )

    access = await resolve.handle(
        ResolveEffectiveAccessQuery(role_ids=frozenset({role_id}))
    )

    assert "ADMIN" in access.role_names
    assert PermissionCode.USERS_READ in access.permission_codes
    assert PermissionCode.USERS_CREATE in access.permission_codes
    assert PermissionCode.USERS_DELETE not in access.permission_codes


@pytest.mark.asyncio
async def test_resolve_empty_roles() -> None:
    resolve = ResolveEffectiveAccessHandler(QueryBus())
    access = await resolve.handle(ResolveEffectiveAccessQuery(role_ids=frozenset()))
    assert access.role_names == frozenset()
    assert access.permission_codes == frozenset()
