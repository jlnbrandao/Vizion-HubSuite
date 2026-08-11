"""Roles HTTP routes — thin adapters over CommandBus / QueryBus."""

from __future__ import annotations

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from src.modules.roles.commands.role_commands import (
    AssignPermissionsToRoleCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    ReplaceRolePermissionsCommand,
    RevokePermissionsFromRoleCommand,
    UpdateRoleCommand,
)
from src.modules.roles.dtos.role_dtos import RoleDto
from src.modules.roles.queries.role_queries import GetRoleByIdQuery, ListRolesQuery
from src.modules.roles.routes.schemas import (
    CreateRoleRequest,
    PermissionIdsRequest,
    RoleIdResponse,
    RoleResponse,
    UpdateRoleRequest,
)
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import require_current_tenant_id

router = APIRouter(prefix="/roles", tags=["roles"])


def _to_response(dto: RoleDto) -> RoleResponse:
    return RoleResponse(
        id=dto.id,
        name=dto.name,
        description=dto.description,
        permission_ids=list(dto.permission_ids),
        is_active=dto.is_active,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


@router.post("", response_model=RoleIdResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_role(
    body: CreateRoleRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_CREATE)),
) -> RoleIdResponse:
    role_id = await command_bus.execute(
        CreateRoleCommand(
            tenant_id=require_current_tenant_id(),
            name=body.name,
            description=body.description,
        )
    )
    return RoleIdResponse(id=role_id)


@router.get("", response_model=list[RoleResponse])
@inject
async def list_roles(
    only_active: bool = False,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_READ)),
) -> list[RoleResponse]:
    items: list[RoleDto] = await query_bus.ask(ListRolesQuery(only_active=only_active))
    return [_to_response(item) for item in items]


@router.get("/{role_id}", response_model=RoleResponse)
@inject
async def get_role(
    role_id: UUID,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_READ)),
) -> RoleResponse:
    dto: RoleDto = await query_bus.ask(GetRoleByIdQuery(role_id=role_id))
    return _to_response(dto)


@router.put("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def update_role(
    role_id: UUID,
    body: UpdateRoleRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_UPDATE)),
) -> None:
    await command_bus.execute(
        UpdateRoleCommand(
            role_id=role_id,
            description=body.description,
            is_active=body.is_active,
        )
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_role(
    role_id: UUID,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_DELETE)),
) -> None:
    await command_bus.execute(DeleteRoleCommand(role_id=role_id))


@router.post("/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def assign_permissions(
    role_id: UUID,
    body: PermissionIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_ASSIGN)),
) -> None:
    await command_bus.execute(
        AssignPermissionsToRoleCommand(
            role_id=role_id,
            permission_ids=frozenset(body.permission_ids),
        )
    )


@router.delete("/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def revoke_permissions(
    role_id: UUID,
    body: PermissionIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_ASSIGN)),
) -> None:
    await command_bus.execute(
        RevokePermissionsFromRoleCommand(
            role_id=role_id,
            permission_ids=frozenset(body.permission_ids),
        )
    )


@router.put("/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def replace_permissions(
    role_id: UUID,
    body: PermissionIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_ASSIGN)),
) -> None:
    await command_bus.execute(
        ReplaceRolePermissionsCommand(
            role_id=role_id,
            permission_ids=frozenset(body.permission_ids),
        )
    )
