"""SCIM 2.0 Users and Groups (Roles) endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.modules.roles.commands.role_commands import CreateRoleCommand, DeleteRoleCommand
from src.modules.roles.queries.role_queries import GetRoleByIdQuery, ListRolesQuery
from src.modules.users.commands.user_commands import (
    CreateUserCommand,
    DeleteUserCommand,
    UpdateUserCommand,
)
from src.modules.users.queries.user_queries import GetUserByIdQuery, ListUsersQuery
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import require_current_tenant_id

router = APIRouter(prefix="/scim/v2", tags=["scim"])


class ScimEmail(BaseModel):
    value: str
    primary: bool = True


class ScimUserResource(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"]
    )
    id: str | None = None
    userName: str
    displayName: str | None = None
    active: bool = True
    emails: list[ScimEmail] = Field(default_factory=list)
    password: str | None = None


class ScimGroupResource(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    )
    id: str | None = None
    displayName: str
    members: list[dict[str, str]] = Field(default_factory=list)


class ScimListResponse(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    )
    totalResults: int
    Resources: list[dict[str, Any]]
    startIndex: int = 1
    itemsPerPage: int = 100


def _user_to_scim(user: Any) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": str(user.id),
        "userName": user.username,
        "displayName": user.full_name,
        "active": user.is_active,
        "emails": [{"value": user.email, "primary": True}],
        "meta": {"resourceType": "User"},
    }


def _role_to_scim(role: Any) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": str(role.id),
        "displayName": role.name,
        "meta": {"resourceType": "Group"},
    }


@router.get("/Users")
@inject
async def list_users(
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=200),
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> ScimListResponse:
    users = await query_bus.ask(ListUsersQuery())
    slice_ = users[startIndex - 1 : startIndex - 1 + count]
    return ScimListResponse(
        totalResults=len(users),
        Resources=[_user_to_scim(u) for u in slice_],
        startIndex=startIndex,
        itemsPerPage=count,
    )


@router.get("/Users/{user_id}")
@inject
async def get_user(
    user_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    return _user_to_scim(user)


@router.post("/Users", status_code=201)
@inject
async def create_user(
    body: ScimUserResource,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    email = body.emails[0].value if body.emails else f"{body.userName}@scim.local"
    password = body.password or "ScimProvision1!"
    user_id = await command_bus.execute(
        CreateUserCommand(
            tenant_id=require_current_tenant_id(),
            email=email,
            username=body.userName[:32],
            full_name=body.displayName or body.userName,
            password=password,
        )
    )
    user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    return _user_to_scim(user)


@router.put("/Users/{user_id}")
@inject
async def replace_user(
    user_id: UUID,
    body: ScimUserResource,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    await command_bus.execute(
        UpdateUserCommand(
            user_id=user_id,
            username=body.userName[:32],
            full_name=body.displayName or body.userName,
            is_active=body.active,
        )
    )
    user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    return _user_to_scim(user)


@router.patch("/Users/{user_id}")
@inject
async def patch_user(
    user_id: UUID,
    body: dict[str, Any],
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    active = body.get("active", user.is_active)
    display = body.get("displayName", user.full_name)
    username = body.get("userName", user.username)
    await command_bus.execute(
        UpdateUserCommand(
            user_id=user_id,
            username=str(username)[:32],
            full_name=str(display),
            is_active=bool(active),
        )
    )
    user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
    return _user_to_scim(user)


@router.delete("/Users/{user_id}", status_code=204)
@inject
async def delete_user(
    user_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
) -> None:
    await command_bus.execute(DeleteUserCommand(user_id=user_id))


@router.get("/Groups")
@inject
async def list_groups(
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> ScimListResponse:
    roles = await query_bus.ask(ListRolesQuery())
    return ScimListResponse(
        totalResults=len(roles),
        Resources=[_role_to_scim(r) for r in roles],
    )


@router.get("/Groups/{group_id}")
@inject
async def get_group(
    group_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    role = await query_bus.ask(GetRoleByIdQuery(role_id=group_id))
    return _role_to_scim(role)


@router.post("/Groups", status_code=201)
@inject
async def create_group(
    body: ScimGroupResource,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
) -> dict[str, Any]:
    role_id = await command_bus.execute(
        CreateRoleCommand(
            tenant_id=require_current_tenant_id(),
            name=body.displayName,
            description="Provisioned via SCIM",
        )
    )
    role = await query_bus.ask(GetRoleByIdQuery(role_id=role_id))
    return _role_to_scim(role)


@router.delete("/Groups/{group_id}", status_code=204)
@inject
async def delete_group(
    group_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SCIM_PROVISION)),
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
) -> None:
    await command_bus.execute(DeleteRoleCommand(role_id=group_id))
