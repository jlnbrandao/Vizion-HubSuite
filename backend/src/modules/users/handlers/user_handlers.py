"""User command and query handlers.

Cross-module: role assignment validates IDs via QueryBus (CheckRolesExistQuery).
Password hashing uses injected PasswordHasher — never done in Domain.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from src.modules.roles.dtos.role_dtos import RolesExistResult
from src.modules.roles.queries.role_queries import CheckRolesExistQuery
from src.modules.users.commands.user_commands import (
    AssignRolesToUserCommand,
    ChangeUserPasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    ReplaceUserRolesCommand,
    RevokeRolesFromUserCommand,
    UpdateUserCommand,
)
from src.modules.users.dtos.user_dtos import UserAuthDto, UserDto
from src.modules.users.entities.user import User
from src.modules.users.queries.user_queries import (
    CountUsersQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    ListUsersQuery,
)
from src.modules.users.repositories.user_repository import UserRepository
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.query_bus import QueryBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import ConflictError, NotFoundError, ValidationError

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


def _to_dto(user: User) -> UserDto:
    return UserDto(
        id=user.id,
        email=user.email.value,
        full_name=user.full_name.value,
        role_ids=tuple(sorted(user.role_ids, key=str)),
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _to_auth_dto(user: User) -> UserAuthDto:
    return UserAuthDto(
        id=user.id,
        email=user.email.value,
        full_name=user.full_name.value,
        hashed_password=user.hashed_password.value,
        role_ids=tuple(sorted(user.role_ids, key=str)),
        is_active=user.is_active,
    )


class CreateUserHandler(CommandHandler[CreateUserCommand, UUID]):
    def __init__(
        self,
        uow_factory: UowFactory,
        users: UserRepository,
        password_hasher: PasswordHasher,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._users = users
        self._password_hasher = password_hasher
        self._query_bus = query_bus

    async def handle(self, command: CreateUserCommand) -> UUID:
        try:
            email = Email.from_primitive(command.email)
            full_name = FullName.from_primitive(command.full_name)
            plain = PlainPassword.from_primitive(command.password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        if command.role_ids:
            await self._ensure_roles_exist(command.role_ids)

        hashed = self._password_hasher.hash(plain)

        async with self._uow_factory() as uow:
            if await self._users.exists_by_email(email):
                raise ConflictError(f"Email already registered: {email.value}")

            user = User.create(email=email, full_name=full_name, hashed_password=hashed)
            if command.role_ids:
                user.assign_roles(set(command.role_ids))

            await self._users.add(user)
            uow.track(user)
            await uow.commit()
            return user.id

    async def _ensure_roles_exist(self, role_ids: frozenset[UUID]) -> None:
        result: RolesExistResult = await self._query_bus.ask(
            CheckRolesExistQuery(role_ids=role_ids)
        )
        if not result.all_exist:
            missing = ", ".join(str(i) for i in sorted(result.missing_ids, key=str))
            raise ValidationError(f"Unknown role ids: {missing}")


class UpdateUserHandler(CommandHandler[UpdateUserCommand, None]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, command: UpdateUserCommand) -> None:
        try:
            full_name = FullName.from_primitive(command.full_name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.change_full_name(full_name)
            if command.is_active:
                user.activate()
            else:
                user.deactivate()

            await self._users.update(user)
            uow.track(user)
            await uow.commit()


class ChangeUserPasswordHandler(CommandHandler[ChangeUserPasswordCommand, None]):
    def __init__(
        self,
        uow_factory: UowFactory,
        users: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._uow_factory = uow_factory
        self._users = users
        self._password_hasher = password_hasher

    async def handle(self, command: ChangeUserPasswordCommand) -> None:
        try:
            plain = PlainPassword.from_primitive(command.new_password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        hashed = self._password_hasher.hash(plain)

        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.change_password(hashed)
            await self._users.update(user)
            uow.track(user)
            await uow.commit()


class DeleteUserHandler(CommandHandler[DeleteUserCommand, None]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, command: DeleteUserCommand) -> None:
        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.mark_deleted()
            await self._users.delete(user)
            uow.track(user)
            await uow.commit()


class AssignRolesToUserHandler(CommandHandler[AssignRolesToUserCommand, None]):
    def __init__(
        self,
        uow_factory: UowFactory,
        users: UserRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._users = users
        self._query_bus = query_bus

    async def handle(self, command: AssignRolesToUserCommand) -> None:
        result: RolesExistResult = await self._query_bus.ask(
            CheckRolesExistQuery(role_ids=command.role_ids)
        )
        if not result.all_exist:
            missing = ", ".join(str(i) for i in sorted(result.missing_ids, key=str))
            raise ValidationError(f"Unknown role ids: {missing}")

        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.assign_roles(set(command.role_ids))
            await self._users.update(user)
            uow.track(user)
            await uow.commit()


class RevokeRolesFromUserHandler(CommandHandler[RevokeRolesFromUserCommand, None]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, command: RevokeRolesFromUserCommand) -> None:
        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.revoke_roles(set(command.role_ids))
            await self._users.update(user)
            uow.track(user)
            await uow.commit()


class ReplaceUserRolesHandler(CommandHandler[ReplaceUserRolesCommand, None]):
    def __init__(
        self,
        uow_factory: UowFactory,
        users: UserRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._users = users
        self._query_bus = query_bus

    async def handle(self, command: ReplaceUserRolesCommand) -> None:
        if command.role_ids:
            result: RolesExistResult = await self._query_bus.ask(
                CheckRolesExistQuery(role_ids=command.role_ids)
            )
            if not result.all_exist:
                missing = ", ".join(str(i) for i in sorted(result.missing_ids, key=str))
                raise ValidationError(f"Unknown role ids: {missing}")

        async with self._uow_factory() as uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {command.user_id}")

            user.replace_roles(set(command.role_ids))
            await self._users.update(user)
            uow.track(user)
            await uow.commit()


class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, UserDto]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, query: GetUserByIdQuery) -> UserDto:
        async with self._uow_factory():
            user = await self._users.get_by_id(query.user_id)
            if user is None:
                raise NotFoundError(f"User not found: {query.user_id}")
            return _to_dto(user)


class GetUserByEmailHandler(QueryHandler[GetUserByEmailQuery, UserAuthDto]):
    """Returns auth-sensitive DTO — consumed by Authentication module later."""

    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, query: GetUserByEmailQuery) -> UserAuthDto:
        try:
            email = Email.from_primitive(query.email)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory():
            user = await self._users.get_by_email(email)
            if user is None:
                raise NotFoundError(f"User not found: {query.email}")
            return _to_auth_dto(user)


class ListUsersHandler(QueryHandler[ListUsersQuery, list[UserDto]]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, query: ListUsersQuery) -> list[UserDto]:
        async with self._uow_factory():
            items = await self._users.list_all(only_active=query.only_active)
            return [_to_dto(item) for item in items]


class CountUsersHandler(QueryHandler[CountUsersQuery, int]):
    def __init__(self, uow_factory: UowFactory, users: UserRepository) -> None:
        self._uow_factory = uow_factory
        self._users = users

    async def handle(self, query: CountUsersQuery) -> int:
        async with self._uow_factory():
            return await self._users.count(only_active=query.only_active)
