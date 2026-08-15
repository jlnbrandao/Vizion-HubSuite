"""Permissions HTTP routes — thin adapters over CommandBus / QueryBus."""

from __future__ import annotations

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from src.modules.permissions.commands.permission_commands import (
    CreatePermissionCommand,
    DeletePermissionCommand,
    UpdatePermissionCommand,
)
from src.modules.permissions.dtos.permission_dtos import PermissionDto
from src.modules.permissions.queries.permission_queries import (
    GetPermissionByIdQuery,
    ListPermissionsQuery,
)
from src.modules.permissions.routes.schemas import (
    CreatePermissionRequest,
    PermissionCatalogEntry,
    PermissionIdResponse,
    PermissionResponse,
    UpdatePermissionRequest,
)
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import (
    get_current_user,
    require_permission,
)
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import require_current_tenant_id

router = APIRouter(prefix="/permissions", tags=["permissions"])


def _to_response(dto: PermissionDto) -> PermissionResponse:
    return PermissionResponse(
        id=dto.id,
        code=dto.code,
        legacy_code=dto.legacy_code,
        service=dto.service,
        resource=dto.resource,
        action=dto.action,
        name=dto.name,
        description=dto.description,
        is_active=dto.is_active,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


@router.post("", response_model=PermissionIdResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_permission(
    body: CreatePermissionRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSIONS_CREATE)),
) -> PermissionIdResponse:
    permission_id = await command_bus.execute(
        CreatePermissionCommand(
            tenant_id=require_current_tenant_id(),
            code=body.code,
            name=body.name,
            description=body.description,
        )
    )
    return PermissionIdResponse(id=permission_id)


@router.get("", response_model=list[PermissionResponse])
@inject
async def list_permissions(
    only_active: bool = False,
    resource: str | None = None,
    action: str | None = None,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSIONS_READ)),
) -> list[PermissionResponse]:
    items: list[PermissionDto] = await query_bus.ask(
        ListPermissionsQuery(
            only_active=only_active,
            resource=resource.strip().lower() if resource else None,
            action=action.strip().lower() if action else None,
        )
    )
    return [_to_response(item) for item in items]


@router.get("/catalog", response_model=list[PermissionCatalogEntry])
async def permission_catalog(
    service: str | None = None,
    _: CurrentUser = Depends(get_current_user),
) -> list[PermissionCatalogEntry]:
    """Canonical catalog from the backend constants — the codegen source of truth."""
    wanted = service.strip().lower() if service else None
    return [
        PermissionCatalogEntry(
            code=item.code,
            legacy_code=item.legacy_code,
            service=item.service,
            resource=item.resource,
            action=item.action,
            name=item.name,
            description=item.description,
        )
        for item in PermissionCode.catalog()
        if wanted is None or item.service == wanted
    ]


@router.get("/{permission_id}", response_model=PermissionResponse)
@inject
async def get_permission(
    permission_id: UUID,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSIONS_READ)),
) -> PermissionResponse:
    dto: PermissionDto = await query_bus.ask(GetPermissionByIdQuery(permission_id=permission_id))
    return _to_response(dto)


@router.put("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def update_permission(
    permission_id: UUID,
    body: UpdatePermissionRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSIONS_UPDATE)),
) -> None:
    await command_bus.execute(
        UpdatePermissionCommand(
            permission_id=permission_id,
            name=body.name,
            description=body.description,
            is_active=body.is_active,
        )
    )


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_permission(
    permission_id: UUID,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSIONS_DELETE)),
) -> None:
    await command_bus.execute(DeletePermissionCommand(permission_id=permission_id))
