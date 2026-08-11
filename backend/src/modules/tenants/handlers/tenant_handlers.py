"""Tenant command and query handlers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from src.modules.tenants.commands.tenant_commands import UpsertTenantCommand
from src.modules.tenants.dtos.tenant_dtos import TenantDto
from src.modules.tenants.entities.tenant import Tenant
from src.modules.tenants.queries.tenant_queries import GetTenantBySlugQuery
from src.modules.tenants.repositories.tenant_repository import TenantRepository
from src.modules.tenants.value_objects.tenant_slug import TenantSlug
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


def _to_dto(tenant: Tenant) -> TenantDto:
    return TenantDto(
        id=tenant.id,
        slug=tenant.slug.value,
        name=tenant.name,
        is_active=tenant.is_active,
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


class UpsertTenantHandler(CommandHandler[UpsertTenantCommand, UUID]):
    """Create or update tenant by slug. Caller must set rls_bypass via ContextVar."""

    def __init__(self, uow_factory: UowFactory, tenants: TenantRepository) -> None:
        self._uow_factory = uow_factory
        self._tenants = tenants

    async def handle(self, command: UpsertTenantCommand) -> UUID:
        try:
            slug = TenantSlug.from_primitive(command.slug)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            tenant = await self._tenants.get_by_slug(slug)
            if tenant is None:
                tenant = Tenant.create(
                    slug=slug,
                    name=command.name,
                    tenant_id=command.tenant_id,
                )
                await self._tenants.add(tenant)
            else:
                tenant.rename(command.name)
                await self._tenants.update(tenant)

            uow.track(tenant)
            await uow.commit()
            return tenant.id
