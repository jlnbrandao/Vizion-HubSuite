"""Handler tests for Roles module including cross-module QueryBus validation."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.permissions.commands.permission_commands import CreatePermissionCommand
from src.modules.permissions.handlers.permission_handlers import (
    CheckPermissionsExistHandler,
    CreatePermissionHandler,
)
from src.modules.permissions.queries.permission_queries import CheckPermissionsExistQuery
from src.modules.permissions.repositories.in_memory_permission_repository import (
    InMemoryPermissionRepository,
)
from src.modules.roles.commands.role_commands import (
    AssignPermissionsToRoleCommand,
    CreateRoleCommand,
    ReplaceRolePermissionsCommand,
    RevokePermissionsFromRoleCommand,
)
from src.modules.roles.handlers.role_handlers import (
    AssignPermissionsToRoleHandler,
    CreateRoleHandler,
    GetRoleByIdHandler,
    ReplaceRolePermissionsHandler,
    RevokePermissionsFromRoleHandler,
)
from src.modules.roles.queries.role_queries import GetRoleByIdQuery
from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import ValidationError
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


@pytest.fixture
def permissions_repo() -> InMemoryPermissionRepository:
    return InMemoryPermissionRepository()


@pytest.fixture
def roles_repo() -> InMemoryRoleRepository:
    return InMemoryRoleRepository()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def uow_factory(event_bus: EventBus):
    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(event_bus)

    return factory


@pytest.fixture
def query_bus(uow_factory, permissions_repo) -> QueryBus:
    bus = QueryBus()
    bus.register(
        CheckPermissionsExistQuery,
        CheckPermissionsExistHandler(uow_factory, permissions_repo),
    )
    return bus


@pytest.mark.asyncio
async def test_create_role_and_assign_valid_permissions(
    permissions_repo, roles_repo, uow_factory, query_bus
) -> None:
    create_perm = CreatePermissionHandler(uow_factory, permissions_repo)
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    assign = AssignPermissionsToRoleHandler(uow_factory, roles_repo, query_bus)
    get_role = GetRoleByIdHandler(uow_factory, roles_repo)

    p1 = await create_perm.handle(CreatePermissionCommand(code="users.read", name="Read"))
    p2 = await create_perm.handle(CreatePermissionCommand(code="users.write", name="Write"))
    role_id = await create_role.handle(CreateRoleCommand(name="ADMIN", description="Full"))

    await assign.handle(
        AssignPermissionsToRoleCommand(role_id=role_id, permission_ids=frozenset({p1, p2}))
    )

    dto = await get_role.handle(GetRoleByIdQuery(role_id=role_id))
    assert set(dto.permission_ids) == {p1, p2}
    assert dto.name == "ADMIN"


@pytest.mark.asyncio
async def test_assign_rejects_unknown_permission_ids(
    roles_repo, uow_factory, query_bus
) -> None:
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    assign = AssignPermissionsToRoleHandler(uow_factory, roles_repo, query_bus)

    role_id = await create_role.handle(CreateRoleCommand(name="VIEWER"))

    with pytest.raises(ValidationError, match="Unknown permission"):
        await assign.handle(
            AssignPermissionsToRoleCommand(
                role_id=role_id,
                permission_ids=frozenset({uuid4()}),
            )
        )


@pytest.mark.asyncio
async def test_replace_and_revoke_permissions(
    permissions_repo, roles_repo, uow_factory, query_bus
) -> None:
    create_perm = CreatePermissionHandler(uow_factory, permissions_repo)
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    replace = ReplaceRolePermissionsHandler(uow_factory, roles_repo, query_bus)
    revoke = RevokePermissionsFromRoleHandler(uow_factory, roles_repo)
    get_role = GetRoleByIdHandler(uow_factory, roles_repo)

    a = await create_perm.handle(CreatePermissionCommand(code="a.read", name="A"))
    b = await create_perm.handle(CreatePermissionCommand(code="b.read", name="B"))
    c = await create_perm.handle(CreatePermissionCommand(code="c.read", name="C"))
    role_id = await create_role.handle(CreateRoleCommand(name="MANAGER"))

    await replace.handle(
        ReplaceRolePermissionsCommand(role_id=role_id, permission_ids=frozenset({a, b}))
    )
    await revoke.handle(
        RevokePermissionsFromRoleCommand(role_id=role_id, permission_ids=frozenset({a}))
    )
    await replace.handle(
        ReplaceRolePermissionsCommand(role_id=role_id, permission_ids=frozenset({b, c}))
    )

    dto = await get_role.handle(GetRoleByIdQuery(role_id=role_id))
    assert set(dto.permission_ids) == {b, c}
