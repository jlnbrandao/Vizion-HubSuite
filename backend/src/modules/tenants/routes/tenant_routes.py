"""Tenants HTTP routes — platform provisioning (requires tenants.* permissions)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.modules.tenants.commands.tenant_commands import (
    ActivateTenantCommand,
    CreateTenantCommand,
    DeactivateTenantCommand,
    RenameTenantCommand,
)
from src.modules.tenants.dtos.tenant_dtos import TenantDto
from src.modules.tenants.queries.tenant_queries import GetTenantByIdQuery, ListTenantsQuery
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool


class TenantIdResponse(BaseModel):
    id: UUID


class CreateTenantRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1, max_length=120)


class RenameTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


def _to_response(dto: TenantDto) -> TenantResponse:
    return TenantResponse(
        id=dto.id,
        slug=dto.slug,
        name=dto.name,
        is_active=dto.is_active,
    )


@asynccontextmanager
async def _platform_catalog_scope():
    """Bypass tenants RLS for platform catalog operations."""
    token = bind_rls_bypass(True)
    try:
        yield
    finally:
        unbind_rls_bypass(token)


@router.get("", response_model=list[TenantResponse])
@inject
async def list_tenants(
    only_active: bool = False,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_READ)),
) -> list[TenantResponse]:
    async with _platform_catalog_scope():
        items: list[TenantDto] = await query_bus.ask(
            ListTenantsQuery(only_active=only_active)
        )
    return [_to_response(item) for item in items]


@router.get("/{tenant_id}", response_model=TenantResponse)
@inject
async def get_tenant(
    tenant_id: UUID,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_READ)),
) -> TenantResponse:
    async with _platform_catalog_scope():
        dto: TenantDto = await query_bus.ask(GetTenantByIdQuery(tenant_id=tenant_id))
    return _to_response(dto)


@router.post("", response_model=TenantIdResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_tenant(
    body: CreateTenantRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_CREATE)),
) -> TenantIdResponse:
    async with _platform_catalog_scope():
        tenant_id = await command_bus.execute(
            CreateTenantCommand(slug=body.slug, name=body.name)
        )
    return TenantIdResponse(id=tenant_id)


@router.put("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def rename_tenant(
    tenant_id: UUID,
    body: RenameTenantRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_UPDATE)),
) -> None:
    async with _platform_catalog_scope():
        await command_bus.execute(
            RenameTenantCommand(tenant_id=tenant_id, name=body.name)
        )


@router.post("/{tenant_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def activate_tenant(
    tenant_id: UUID,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_ACTIVATE)),
) -> None:
    async with _platform_catalog_scope():
        await command_bus.execute(ActivateTenantCommand(tenant_id=tenant_id))


@router.post("/{tenant_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def deactivate_tenant(
    tenant_id: UUID,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.TENANTS_DEACTIVATE)),
) -> None:
    async with _platform_catalog_scope():
        await command_bus.execute(DeactivateTenantCommand(tenant_id=tenant_id))
