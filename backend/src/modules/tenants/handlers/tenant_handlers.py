"""Tenant command and query handlers.

Platform mutations require rls_bypass (set by routes / seed).
Host resolution uses resolve_tenant_by_slug (SECURITY DEFINER) without bypass.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from src.modules.permissions.commands.permission_commands import CreatePermissionCommand
from src.modules.permissions.dtos.permission_dtos import PermissionDto
from src.modules.permissions.queries.permission_queries import ListPermissionsQuery
from src.modules.roles.commands.role_commands import (
    CreateRoleCommand,
    ReplaceRolePermissionsCommand,
)
from src.modules.tenants.commands.tenant_commands import (
    ActivateTenantCommand,
    CreateTenantCommand,
    DeactivateTenantCommand,
    RenameTenantCommand,
    UpsertTenantCommand,
)
from src.modules.tenants.dtos.tenant_dtos import TenantAdminDto, TenantDto
from src.modules.tenants.entities.tenant import Tenant
from src.modules.tenants.queries.tenant_queries import (
    GetTenantByIdQuery,
    GetTenantBySlugQuery,
    ListTenantsQuery,
)
from src.modules.tenants.repositories.tenant_repository import TenantRepository
from src.modules.tenants.value_objects.tenant_slug import TenantSlug
from src.modules.users.commands.user_commands import CreateUserCommand
from src.modules.users.dtos.user_dtos import UserSummaryDto
from src.modules.users.queries.user_queries import ResolveTenantAdminsQuery
from src.shared.application.command_bus import CommandBus
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.query_bus import QueryBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import ConflictError, NotFoundError, ValidationError
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import (
    bind_rls_bypass,
    bind_tenant,
    unbind_rls_bypass,
    unbind_tenant,
)

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]

_ADMIN_ROLE = "ADMIN"
_ADMIN_ROLE_DESCRIPTION = "CRUD for users, roles, and permissions"


def _admin_dto(summary: UserSummaryDto | None) -> TenantAdminDto | None:
    if summary is None:
        return None
    return TenantAdminDto(
        id=summary.id,
        username=summary.username,
        email=summary.email,
        full_name=summary.full_name,
    )


def _to_dto(tenant: Tenant, *, admin: TenantAdminDto | None = None) -> TenantDto:
    return TenantDto(
        id=tenant.id,
        slug=tenant.slug.value,
        name=tenant.name,
        is_active=tenant.is_active,
        admin=admin,
    )


class GetTenantBySlugHandler(QueryHandler[GetTenantBySlugQuery, TenantDto]):
    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, query: GetTenantBySlugQuery) -> TenantDto:
        try:
            slug = TenantSlug.from_primitive(query.slug)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory():
            tenant = await self._tenants.get_by_slug(slug)
            if tenant is None or not tenant.is_active:
                raise NotFoundError(f"Tenant not found: {query.slug}")
            return _to_dto(tenant)


class GetTenantByIdHandler(QueryHandler[GetTenantByIdQuery, TenantDto]):
    def __init__(
        self,
        uow_factory: UowFactory,
        tenants: TenantRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants
        self._query_bus = query_bus

    async def handle(self, query: GetTenantByIdQuery) -> TenantDto:
        async with self._uow_factory():
            tenant = await self._tenants.get_by_id(query.tenant_id)
            if tenant is None:
                raise NotFoundError(f"Tenant not found: {query.tenant_id}")

        admins: dict[UUID, UserSummaryDto] = await self._query_bus.ask(
            ResolveTenantAdminsQuery(tenant_ids=frozenset({tenant.id}))
        )
        return _to_dto(tenant, admin=_admin_dto(admins.get(tenant.id)))


class ListTenantsHandler(QueryHandler[ListTenantsQuery, list[TenantDto]]):
    def __init__(
        self,
        uow_factory: UowFactory,
        tenants: TenantRepository,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants
        self._query_bus = query_bus

    async def handle(self, query: ListTenantsQuery) -> list[TenantDto]:
        async with self._uow_factory():
            items = await self._tenants.list_all(only_active=query.only_active)

        if not items:
            return []

        admins: dict[UUID, UserSummaryDto] = await self._query_bus.ask(
            ResolveTenantAdminsQuery(
                tenant_ids=frozenset(item.id for item in items),
            )
        )
        return [
            _to_dto(item, admin=_admin_dto(admins.get(item.id))) for item in items
        ]


class UpsertTenantHandler(CommandHandler[UpsertTenantCommand, UUID]):
    """Create or update tenant by id (preferred) or slug. Caller must set rls_bypass."""

    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, command: UpsertTenantCommand) -> UUID:
        try:
            slug = TenantSlug.from_primitive(command.slug)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            tenant = None
            if command.tenant_id is not None:
                tenant = await self._tenants.get_by_id(command.tenant_id)
            if tenant is None:
                tenant = await self._tenants.get_by_slug(slug)

            if tenant is None:
                tenant = Tenant.create(
                    slug=slug,
                    name=command.name,
                    tenant_id=command.tenant_id,
                )
                await self._tenants.add(tenant)
            else:
                existing_slug = await self._tenants.get_by_slug(slug)
                if existing_slug is not None and existing_slug.id != tenant.id:
                    raise ConflictError(f"Tenant already exists: {slug.value}")
                tenant.change_slug(slug)
                tenant.rename(command.name)
                await self._tenants.update(tenant)

            uow.track(tenant)
            await uow.commit()
            return tenant.id


class CreateTenantHandler(CommandHandler[CreateTenantCommand, UUID]):
    """Create tenant row, then bootstrap ADMIN role permissions + Administrator user."""

    def __init__(
        self,
        uow_factory: UowFactory,
        tenants: TenantRepository,
        command_bus: CommandBus,
        query_bus: QueryBus,
    ) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def handle(self, command: CreateTenantCommand) -> UUID:
        try:
            slug = TenantSlug.from_primitive(command.slug)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            existing = await self._tenants.get_by_slug(slug)
            if existing is not None:
                raise ConflictError(f"Tenant already exists: {slug.value}")
            tenant = Tenant.create(slug=slug, name=command.name)
            await self._tenants.add(tenant)
            uow.track(tenant)
            await uow.commit()
            tenant_id = tenant.id

        bypass_token = bind_rls_bypass(False)
        id_token, slug_token, name_token = bind_tenant(
            tenant_id, slug=slug.value, name=command.name
        )
        try:
            await self._provision_administrator(tenant_id, command)
        finally:
            unbind_tenant(id_token, slug_token, name_token)
            unbind_rls_bypass(bypass_token)

        return tenant_id

    async def _provision_administrator(
        self, tenant_id: UUID, command: CreateTenantCommand
    ) -> None:
        code_to_id = await self._ensure_admin_permissions(tenant_id)
        role_id = await self._command_bus.execute(
            CreateRoleCommand(
                tenant_id=tenant_id,
                name=_ADMIN_ROLE,
                description=_ADMIN_ROLE_DESCRIPTION,
            )
        )
        await self._command_bus.execute(
            ReplaceRolePermissionsCommand(
                role_id=role_id,
                permission_ids=frozenset(code_to_id[code] for code in code_to_id),
            )
        )
        await self._command_bus.execute(
            CreateUserCommand(
                tenant_id=tenant_id,
                email=command.admin_email,
                username=command.admin_username,
                full_name=command.admin_full_name,
                password=command.admin_password,
                role_ids=frozenset({role_id}),
            )
        )

    async def _ensure_admin_permissions(self, tenant_id: UUID) -> dict[str, UUID]:
        existing: list[PermissionDto] = await self._query_bus.ask(ListPermissionsQuery())
        code_to_id = {item.code: item.id for item in existing}
        for code in sorted(PermissionCode.admin_role_codes()):
            if code in code_to_id:
                continue
            definition = PermissionCode.definition_for(code)
            name = definition.name if definition else code
            description = definition.description if definition else f"Permission {code}"
            permission_id = await self._command_bus.execute(
                CreatePermissionCommand(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    description=description,
                )
            )
            code_to_id[code] = permission_id
        return {code: code_to_id[code] for code in PermissionCode.admin_role_codes()}


class RenameTenantHandler(CommandHandler[RenameTenantCommand, None]):
    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, command: RenameTenantCommand) -> None:
        async with self._uow_factory() as uow:
            tenant = await self._tenants.get_by_id(command.tenant_id)
            if tenant is None:
                raise NotFoundError(f"Tenant not found: {command.tenant_id}")
            tenant.rename(command.name)
            await self._tenants.update(tenant)
            uow.track(tenant)
            await uow.commit()


class ActivateTenantHandler(CommandHandler[ActivateTenantCommand, None]):
    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, command: ActivateTenantCommand) -> None:
        async with self._uow_factory() as uow:
            tenant = await self._tenants.get_by_id(command.tenant_id)
            if tenant is None:
                raise NotFoundError(f"Tenant not found: {command.tenant_id}")
            tenant.activate()
            await self._tenants.update(tenant)
            uow.track(tenant)
            await uow.commit()


class DeactivateTenantHandler(CommandHandler[DeactivateTenantCommand, None]):
    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, command: DeactivateTenantCommand) -> None:
        async with self._uow_factory() as uow:
            tenant = await self._tenants.get_by_id(command.tenant_id)
            if tenant is None:
                raise NotFoundError(f"Tenant not found: {command.tenant_id}")
            tenant.deactivate()
            await self._tenants.update(tenant)
            uow.track(tenant)
            await uow.commit()
