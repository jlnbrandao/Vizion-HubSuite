"""Role command and query handlers.

Cross-module: Assign/Replace permissions validate IDs via QueryBus
(CheckPermissionsExistQuery) — never imports Permissions domain internals.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from src.modules.permissions.dtos.permission_dtos import PermissionsExistResult
from src.modules.permissions.queries.permission_queries import CheckPermissionsExistQuery
from src.modules.roles.commands.role_commands import (
    AssignPermissionsToRoleCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    ReplaceRolePermissionsCommand,
    RevokePermissionsFromRoleCommand,
    UpdateRoleCommand,
)
from src.modules.roles.dtos.role_dtos import RoleDto, RolesExistResult
from src.modules.roles.entities.role import Role
from src.modules.roles.queries.role_queries import (
    CheckRolesExistQuery,
    CountRolesQuery,
    GetRoleByIdQuery,
    GetRolesByIdsQuery,
    ListRolesQuery,
)
from src.modules.roles.repositories.role_repository import RoleRepository
from src.modules.roles.value_objects.role_description import RoleDescription
from src.modules.roles.value_objects.role_name import RoleName
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.query_bus import QueryBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import ConflictError, NotFoundError, ValidationError

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


def _to_dto(role: Role) -> RoleDto:
    return RoleDto(
        id=role.id,
        name=role.name.value,
        description=role.description.value,
        permission_ids=tuple(sorted(role.permission_ids, key=str)),
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


class CreateRoleHandler(CommandHandler[CreateRoleCommand, UUID]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, command: CreateRoleCommand) -> UUID:
        try:
            name = RoleName.from_primitive(command.name)
            description = RoleDescription.from_primitive(command.description)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            if await self._roles.exists_by_name(name):
                raise ConflictError(f"Role already exists: {name.value}")

            role = Role.create(
                tenant_id=command.tenant_id,
                name=name,
                description=description,
            )
            await self._roles.add(role)
            uow.track(role)
            await uow.commit()
            return role.id


class UpdateRoleHandler(CommandHandler[UpdateRoleCommand, None]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, command: UpdateRoleCommand) -> None:
        try:
            description = RoleDescription.from_primitive(command.description)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {command.role_id}")

            role.change_description(description)
            if command.is_active:
                role.activate()
            else:
                role.deactivate()

            await self._roles.update(role)
            uow.track(role)
            await uow.commit()


class DeleteRoleHandler(CommandHandler[DeleteRoleCommand, None]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, command: DeleteRoleCommand) -> None:
        async with self._uow_factory() as uow:
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {command.role_id}")

            role.mark_deleted()
            await self._roles.delete(role)
            uow.track(role)
            await uow.commit()


class AssignPermissionsToRoleHandler(CommandHandler[AssignPermissionsToRoleCommand, None]):
    def __init__(
        self,
        uow_factory: UowFactory,
        roles: RoleRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._roles = roles
        self._query_bus = query_bus

    async def handle(self, command: AssignPermissionsToRoleCommand) -> None:
        await self._ensure_permissions_exist(command.permission_ids)

        async with self._uow_factory() as uow:
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {command.role_id}")

            role.assign_permissions(set(command.permission_ids))
            await self._roles.update(role)
            uow.track(role)
            await uow.commit()

    async def _ensure_permissions_exist(self, permission_ids: frozenset[UUID]) -> None:
        result: PermissionsExistResult = await self._query_bus.ask(
            CheckPermissionsExistQuery(permission_ids=permission_ids)
        )
        if not result.all_exist:
            missing = ", ".join(str(i) for i in sorted(result.missing_ids, key=str))
            raise ValidationError(f"Unknown permission ids: {missing}")


class RevokePermissionsFromRoleHandler(CommandHandler[RevokePermissionsFromRoleCommand, None]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, command: RevokePermissionsFromRoleCommand) -> None:
        async with self._uow_factory() as uow:
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {command.role_id}")

            role.revoke_permissions(set(command.permission_ids))
            await self._roles.update(role)
            uow.track(role)
            await uow.commit()


class ReplaceRolePermissionsHandler(CommandHandler[ReplaceRolePermissionsCommand, None]):
    def __init__(
        self,
        uow_factory: UowFactory,
        roles: RoleRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._roles = roles
        self._query_bus = query_bus

    async def handle(self, command: ReplaceRolePermissionsCommand) -> None:
        if command.permission_ids:
            result: PermissionsExistResult = await self._query_bus.ask(
                CheckPermissionsExistQuery(permission_ids=command.permission_ids)
            )
            if not result.all_exist:
                missing = ", ".join(str(i) for i in sorted(result.missing_ids, key=str))
                raise ValidationError(f"Unknown permission ids: {missing}")

        async with self._uow_factory() as uow:
            role = await self._roles.get_by_id(command.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {command.role_id}")

            role.replace_permissions(set(command.permission_ids))
            await self._roles.update(role)
            uow.track(role)
            await uow.commit()


class GetRoleByIdHandler(QueryHandler[GetRoleByIdQuery, RoleDto]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, query: GetRoleByIdQuery) -> RoleDto:
        async with self._uow_factory():
            role = await self._roles.get_by_id(query.role_id)
            if role is None:
                raise NotFoundError(f"Role not found: {query.role_id}")
            return _to_dto(role)


class ListRolesHandler(QueryHandler[ListRolesQuery, list[RoleDto]]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, query: ListRolesQuery) -> list[RoleDto]:
        async with self._uow_factory():
            items = await self._roles.list_all(only_active=query.only_active)
            return [_to_dto(item) for item in items]


class CheckRolesExistHandler(QueryHandler[CheckRolesExistQuery, RolesExistResult]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, query: CheckRolesExistQuery) -> RolesExistResult:
        if not query.role_ids:
            return RolesExistResult(all_exist=True, missing_ids=frozenset())

        async with self._uow_factory():
            found = await self._roles.find_by_ids(set(query.role_ids))
            found_ids = {item.id for item in found}
            missing = frozenset(query.role_ids - found_ids)
            return RolesExistResult(all_exist=not missing, missing_ids=missing)


class GetRolesByIdsHandler(QueryHandler[GetRolesByIdsQuery, list[RoleDto]]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, query: GetRolesByIdsQuery) -> list[RoleDto]:
        if not query.role_ids:
            return []
        async with self._uow_factory():
            items = await self._roles.find_by_ids(set(query.role_ids))
            return [_to_dto(item) for item in items if item.is_active]


class CountRolesHandler(QueryHandler[CountRolesQuery, int]):
    def __init__(self, uow_factory: UowFactory, roles: RoleRepository) -> None:
        self._uow_factory = uow_factory
        self._roles = roles

    async def handle(self, query: CountRolesQuery) -> int:
        async with self._uow_factory():
            return await self._roles.count(only_active=query.only_active)
