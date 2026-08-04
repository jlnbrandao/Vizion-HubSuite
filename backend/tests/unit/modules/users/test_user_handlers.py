"""Handler tests for Users module (in-memory + fake hasher)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.roles.commands.role_commands import CreateRoleCommand
from src.modules.roles.handlers.role_handlers import CheckRolesExistHandler, CreateRoleHandler
from src.modules.roles.queries.role_queries import CheckRolesExistQuery
from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository
from src.modules.users.commands.user_commands import (
    AssignRolesToUserCommand,
    ChangeUserPasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    ReplaceUserRolesCommand,
    UpdateUserCommand,
)
from src.modules.users.handlers.user_handlers import (
    AssignRolesToUserHandler,
    ChangeUserPasswordHandler,
    CreateUserHandler,
    DeleteUserHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    ListUsersHandler,
    ReplaceUserRolesHandler,
    UpdateUserHandler,
)
from src.modules.users.queries.user_queries import (
    GetUserByEmailQuery,
    GetUserByIdQuery,
    ListUsersQuery,
)
from src.modules.users.repositories.in_memory_user_repository import InMemoryUserRepository
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import ConflictError, ValidationError
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


class FakePasswordHasher(PasswordHasher):
    def hash(self, plain: PlainPassword) -> HashedPassword:
        return HashedPassword(value=f"hashed::{plain.value}::{'x' * 40}")

    def verify(self, plain: PlainPassword, hashed: HashedPassword) -> bool:
        return hashed.value == f"hashed::{plain.value}::{'x' * 40}"


@pytest.fixture
def users_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


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
def password_hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def query_bus(uow_factory, roles_repo) -> QueryBus:
    bus = QueryBus()
    bus.register(CheckRolesExistQuery, CheckRolesExistHandler(uow_factory, roles_repo))
    return bus


@pytest.mark.asyncio
async def test_create_user_with_roles(
    users_repo, roles_repo, uow_factory, password_hasher, query_bus
) -> None:
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    create_user = CreateUserHandler(uow_factory, users_repo, password_hasher, query_bus)
    get_user = GetUserByIdHandler(uow_factory, users_repo)

    role_id = await create_role.handle(CreateRoleCommand(name="ADMIN"))
    user_id = await create_user.handle(
        CreateUserCommand(
            email="admin@lanstar.io",
            full_name="System Admin",
            password="Secret123",
            role_ids=frozenset({role_id}),
        )
    )

    dto = await get_user.handle(GetUserByIdQuery(user_id=user_id))
    assert dto.email == "admin@lanstar.io"
    assert role_id in dto.role_ids


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    users_repo, uow_factory, password_hasher, query_bus
) -> None:
    create_user = CreateUserHandler(uow_factory, users_repo, password_hasher, query_bus)
    await create_user.handle(
        CreateUserCommand(email="a@b.com", full_name="A B", password="Secret123")
    )

    with pytest.raises(ConflictError):
        await create_user.handle(
            CreateUserCommand(email="A@B.com", full_name="Other", password="Secret123")
        )


@pytest.mark.asyncio
async def test_assign_rejects_unknown_roles(
    users_repo, uow_factory, password_hasher, query_bus
) -> None:
    create_user = CreateUserHandler(uow_factory, users_repo, password_hasher, query_bus)
    assign = AssignRolesToUserHandler(uow_factory, users_repo, query_bus)

    user_id = await create_user.handle(
        CreateUserCommand(email="u@x.com", full_name="User X", password="Secret123")
    )

    with pytest.raises(ValidationError, match="Unknown role"):
        await assign.handle(
            AssignRolesToUserCommand(user_id=user_id, role_ids=frozenset({uuid4()}))
        )


@pytest.mark.asyncio
async def test_update_password_list_replace_delete(
    users_repo, roles_repo, uow_factory, password_hasher, query_bus
) -> None:
    create_role = CreateRoleHandler(uow_factory, roles_repo)
    create_user = CreateUserHandler(uow_factory, users_repo, password_hasher, query_bus)
    update = UpdateUserHandler(uow_factory, users_repo)
    change_pwd = ChangeUserPasswordHandler(uow_factory, users_repo, password_hasher)
    replace = ReplaceUserRolesHandler(uow_factory, users_repo, query_bus)
    list_users = ListUsersHandler(uow_factory, users_repo)
    get_by_email = GetUserByEmailHandler(uow_factory, users_repo)
    delete = DeleteUserHandler(uow_factory, users_repo)

    r1 = await create_role.handle(CreateRoleCommand(name="MANAGER"))
    r2 = await create_role.handle(CreateRoleCommand(name="VIEWER"))
    user_id = await create_user.handle(
        CreateUserCommand(email="m@x.com", full_name="Mgr", password="Secret123")
    )

    await update.handle(UpdateUserCommand(user_id=user_id, full_name="Manager User"))
    await change_pwd.handle(
        ChangeUserPasswordCommand(user_id=user_id, new_password="NewSecret1")
    )
    await replace.handle(
        ReplaceUserRolesCommand(user_id=user_id, role_ids=frozenset({r1, r2}))
    )

    users = await list_users.handle(ListUsersQuery())
    assert len(users) == 1
    assert users[0].full_name == "Manager User"
    assert set(users[0].role_ids) == {r1, r2}

    auth = await get_by_email.handle(GetUserByEmailQuery(email="m@x.com"))
    assert auth.hashed_password.startswith("hashed::NewSecret1")

    await delete.handle(DeleteUserCommand(user_id=user_id))
    assert await list_users.handle(ListUsersQuery()) == []
