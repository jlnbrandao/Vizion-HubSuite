"""Handler tests for Permissions module (in-memory)."""

from __future__ import annotations

import pytest

from src.modules.permissions.commands.permission_commands import (
    CreatePermissionCommand,
    DeletePermissionCommand,
    UpdatePermissionCommand,
)
from src.modules.permissions.handlers.permission_handlers import (
    CheckPermissionsExistHandler,
    CreatePermissionHandler,
    DeletePermissionHandler,
    GetPermissionByIdHandler,
    ListPermissionsHandler,
    UpdatePermissionHandler,
)
from src.modules.permissions.queries.permission_queries import (
    CheckPermissionsExistQuery,
    GetPermissionByIdQuery,
    ListPermissionsQuery,
)
from src.modules.permissions.repositories.in_memory_permission_repository import (
    InMemoryPermissionRepository,
)
from src.shared.application.event_bus import EventBus
from src.shared.infrastructure.exceptions import ConflictError, NotFoundError
from tests.unit.conftest import UNIVERSE_TENANT_ID
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


@pytest.fixture
def permissions_repo() -> InMemoryPermissionRepository:
    return InMemoryPermissionRepository()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def uow_factory(event_bus: EventBus):
    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(event_bus)

    return factory


@pytest.mark.asyncio
async def test_create_and_get_permission(permissions_repo, uow_factory) -> None:
    create = CreatePermissionHandler(uow_factory, permissions_repo)
    get_one = GetPermissionByIdHandler(uow_factory, permissions_repo)

    permission_id = await create.handle(
        CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="users.create", name="Create User")
    )
    dto = await get_one.handle(GetPermissionByIdQuery(permission_id=permission_id))

    assert dto.code == "users.create"
    assert dto.resource == "users"
    assert dto.action == "create"
    assert dto.name == "Create User"


@pytest.mark.asyncio
async def test_list_permissions_filters_by_resource_and_action(
    permissions_repo, uow_factory
) -> None:
    create = CreatePermissionHandler(uow_factory, permissions_repo)
    list_all = ListPermissionsHandler(uow_factory, permissions_repo)

    await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="users.create", name="Create User"))
    await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="users.read", name="Read User"))
    await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="roles.read", name="Read Role"))

    by_users = await list_all.handle(ListPermissionsQuery(resource="users"))
    assert [item.code for item in by_users] == ["users.create", "users.read"]

    by_read = await list_all.handle(ListPermissionsQuery(action="read"))
    assert [item.code for item in by_read] == ["roles.read", "users.read"]

    by_both = await list_all.handle(ListPermissionsQuery(resource="users", action="create"))
    assert [item.code for item in by_both] == ["users.create"]


@pytest.mark.asyncio
async def test_create_permission_conflict(permissions_repo, uow_factory) -> None:
    create = CreatePermissionHandler(uow_factory, permissions_repo)
    await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="users.read", name="Read"))

    with pytest.raises(ConflictError):
        await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="users.read", name="Read again"))


@pytest.mark.asyncio
async def test_update_list_delete_permission(permissions_repo, uow_factory) -> None:
    create = CreatePermissionHandler(uow_factory, permissions_repo)
    update = UpdatePermissionHandler(uow_factory, permissions_repo)
    list_all = ListPermissionsHandler(uow_factory, permissions_repo)
    delete = DeletePermissionHandler(uow_factory, permissions_repo)

    permission_id = await create.handle(
        CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="roles.read", name="Read Roles")
    )
    await update.handle(
        UpdatePermissionCommand(
            permission_id=permission_id,
            name="View Roles",
            description="updated",
            is_active=True,
        )
    )

    items = await list_all.handle(ListPermissionsQuery())
    assert len(items) == 1
    assert items[0].name == "View Roles"

    await delete.handle(DeletePermissionCommand(permission_id=permission_id))
    assert await list_all.handle(ListPermissionsQuery()) == []


@pytest.mark.asyncio
async def test_check_permissions_exist(permissions_repo, uow_factory) -> None:
    create = CreatePermissionHandler(uow_factory, permissions_repo)
    check = CheckPermissionsExistHandler(uow_factory, permissions_repo)

    pid = await create.handle(CreatePermissionCommand(tenant_id=UNIVERSE_TENANT_ID,code="a.read", name="A"))
    from uuid import uuid4

    missing = uuid4()
    result = await check.handle(
        CheckPermissionsExistQuery(permission_ids=frozenset({pid, missing}))
    )
    assert result.all_exist is False
    assert missing in result.missing_ids


@pytest.mark.asyncio
async def test_get_permission_not_found(permissions_repo, uow_factory) -> None:
    get_one = GetPermissionByIdHandler(uow_factory, permissions_repo)
    from uuid import uuid4

    with pytest.raises(NotFoundError):
        await get_one.handle(GetPermissionByIdQuery(permission_id=uuid4()))
