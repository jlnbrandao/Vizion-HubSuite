"""Users HTTP routes — thin adapters over CommandBus / QueryBus."""

from __future__ import annotations

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from src.modules.users.commands.user_commands import (
    AssignRolesToUserCommand,
    ChangeUserPasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    ReplaceUserRolesCommand,
    RevokeRolesFromUserCommand,
    UpdateUserCommand,
)
from src.modules.users.dtos.user_dtos import UserDto
from src.modules.users.queries.user_queries import GetUserByIdQuery, ListUsersQuery
from src.modules.users.routes.schemas import (
    ChangePasswordRequest,
    CreateUserRequest,
    RoleIdsRequest,
    UpdateUserRequest,
    UserIdResponse,
    UserResponse,
)
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(dto: UserDto) -> UserResponse:
    return UserResponse(
        id=dto.id,
        email=dto.email,
        full_name=dto.full_name,
        role_ids=list(dto.role_ids),
        is_active=dto.is_active,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


@router.post("", response_model=UserIdResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    body: CreateUserRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_CREATE)),
) -> UserIdResponse:
    user_id = await command_bus.execute(
        CreateUserCommand(
            email=body.email,
            full_name=body.full_name,
            password=body.password,
            role_ids=frozenset(body.role_ids),
        )
    )
    return UserIdResponse(id=user_id)


@router.get("", response_model=list[UserResponse])
@inject
async def list_users(
    only_active: bool = False,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_READ)),
) -> list[UserResponse]:
    items: list[UserDto] = await query_bus.ask(ListUsersQuery(only_active=only_active))
    return [_to_response(item) for item in items]


@router.get("/{user_id}", response_model=UserResponse)
@inject
async def get_user(
    user_id: UUID,
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_READ)),
) -> UserResponse:
    dto: UserDto = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    return _to_response(dto)


@router.put("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_UPDATE)),
) -> None:
    await command_bus.execute(
        UpdateUserCommand(
            user_id=user_id,
            full_name=body.full_name,
            is_active=body.is_active,
        )
    )


@router.post("/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def change_password(
    user_id: UUID,
    body: ChangePasswordRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_UPDATE)),
) -> None:
    await command_bus.execute(
        ChangeUserPasswordCommand(user_id=user_id, new_password=body.new_password)
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_user(
    user_id: UUID,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_DELETE)),
) -> None:
    await command_bus.execute(DeleteUserCommand(user_id=user_id))


@router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def assign_roles(
    user_id: UUID,
    body: RoleIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_ASSIGN_ROLES)),
) -> None:
    await command_bus.execute(
        AssignRolesToUserCommand(user_id=user_id, role_ids=frozenset(body.role_ids))
    )


@router.delete("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def revoke_roles(
    user_id: UUID,
    body: RoleIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_ASSIGN_ROLES)),
) -> None:
    await command_bus.execute(
        RevokeRolesFromUserCommand(user_id=user_id, role_ids=frozenset(body.role_ids))
    )


@router.put("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def replace_roles(
    user_id: UUID,
    body: RoleIdsRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.USERS_ASSIGN_ROLES)),
) -> None:
    await command_bus.execute(
        ReplaceUserRolesCommand(user_id=user_id, role_ids=frozenset(body.role_ids))
    )
