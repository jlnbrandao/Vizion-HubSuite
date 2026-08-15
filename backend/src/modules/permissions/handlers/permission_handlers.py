"""Permission command and query handlers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from src.modules.permissions.commands.permission_commands import (
    CreatePermissionCommand,
    DeletePermissionCommand,
    UpdatePermissionCommand,
)
from src.modules.permissions.dtos.permission_dtos import (
    PermissionDto,
    PermissionsExistResult,
)
from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.queries.permission_queries import (
    CheckPermissionsExistQuery,
    CountPermissionsQuery,
    GetPermissionByIdQuery,
    GetPermissionsByIdsQuery,
    ListPermissionsQuery,
)
from src.modules.permissions.repositories.permission_repository import PermissionRepository
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from src.shared.infrastructure.security.permission_codes import (
    PermissionCode as CatalogPermissionCode,
)
from src.shared.infrastructure.tenant_context import get_rls_bypass

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


def _to_dto(permission: Permission) -> PermissionDto:
    code = permission.code.value
    return PermissionDto(
        id=permission.id,
        code=code,
        legacy_code=CatalogPermissionCode.legacy(code),
        service=permission.code.service or CatalogPermissionCode.service_of(code),
        resource=permission.code.resource,
        action=permission.code.action,
        name=permission.name.value,
        description=permission.description,
        is_active=permission.is_active,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


class CreatePermissionHandler(CommandHandler[CreatePermissionCommand, UUID]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, command: CreatePermissionCommand) -> UUID:
        try:
            # Catalog codes are stored namespaced; legacy input is canonicalized here.
            code = PermissionCode.from_primitive(
                CatalogPermissionCode.canonical(command.code.strip().lower())
            )
            name = PermissionName.from_primitive(command.name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        if (
            code.value in CatalogPermissionCode.platform_only_codes()
            and not get_rls_bypass()
        ):
            raise ForbiddenError(
                f"Platform-only permission cannot be created in tenant scope: {code.value}"
            )

        async with self._uow_factory() as uow:
            if await self._permissions.exists_by_code(code):
                raise ConflictError(f"Permission code already exists: {code.value}")

            permission = Permission.create(
                tenant_id=command.tenant_id,
                code=code,
                name=name,
                description=command.description,
            )
            await self._permissions.add(permission)
            uow.track(permission)
            await uow.commit()
            return permission.id


class UpdatePermissionHandler(CommandHandler[UpdatePermissionCommand, None]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, command: UpdatePermissionCommand) -> None:
        try:
            name = PermissionName.from_primitive(command.name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            permission = await self._permissions.get_by_id(command.permission_id)
            if permission is None:
                raise NotFoundError(f"Permission not found: {command.permission_id}")

            permission.rename(name)
            permission.change_description(command.description)
            if command.is_active:
                permission.activate()
            else:
                permission.deactivate()

            await self._permissions.update(permission)
            uow.track(permission)
            await uow.commit()


class DeletePermissionHandler(CommandHandler[DeletePermissionCommand, None]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, command: DeletePermissionCommand) -> None:
        async with self._uow_factory() as uow:
            permission = await self._permissions.get_by_id(command.permission_id)
            if permission is None:
                raise NotFoundError(f"Permission not found: {command.permission_id}")

            permission.mark_deleted()
            await self._permissions.delete(permission)
            uow.track(permission)
            await uow.commit()


class GetPermissionByIdHandler(QueryHandler[GetPermissionByIdQuery, PermissionDto]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, query: GetPermissionByIdQuery) -> PermissionDto:
        async with self._uow_factory():
            permission = await self._permissions.get_by_id(query.permission_id)
            if permission is None:
                raise NotFoundError(f"Permission not found: {query.permission_id}")
            return _to_dto(permission)


class ListPermissionsHandler(QueryHandler[ListPermissionsQuery, list[PermissionDto]]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, query: ListPermissionsQuery) -> list[PermissionDto]:
        async with self._uow_factory():
            items = await self._permissions.list_all(
                only_active=query.only_active,
                resource=query.resource,
                action=query.action,
            )
            return [_to_dto(item) for item in items]


class CheckPermissionsExistHandler(
    QueryHandler[CheckPermissionsExistQuery, PermissionsExistResult]
):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, query: CheckPermissionsExistQuery) -> PermissionsExistResult:
        if not query.permission_ids:
            return PermissionsExistResult(all_exist=True, missing_ids=frozenset())

        async with self._uow_factory():
            found = await self._permissions.find_by_ids(set(query.permission_ids))
            found_ids = {item.id for item in found}
            missing = frozenset(query.permission_ids - found_ids)
            return PermissionsExistResult(all_exist=not missing, missing_ids=missing)


class GetPermissionsByIdsHandler(
    QueryHandler[GetPermissionsByIdsQuery, list[PermissionDto]]
):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, query: GetPermissionsByIdsQuery) -> list[PermissionDto]:
        if not query.permission_ids:
            return []
        async with self._uow_factory():
            items = await self._permissions.find_by_ids(set(query.permission_ids))
            return [_to_dto(item) for item in items if item.is_active]


class CountPermissionsHandler(QueryHandler[CountPermissionsQuery, int]):
    def __init__(self, uow_factory: UowFactory, permissions: PermissionRepository) -> None:
        self._uow_factory = uow_factory
        self._permissions = permissions

    async def handle(self, query: CountPermissionsQuery) -> int:
        async with self._uow_factory():
            return await self._permissions.count(only_active=query.only_active)
