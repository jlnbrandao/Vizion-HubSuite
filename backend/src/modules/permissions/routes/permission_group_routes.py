"""Permission bundle routes — compose roles from service-scoped sets of codes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from src.modules.permissions.groups.service import (
    PermissionGroupService,
    PermissionGroupView,
)
from src.modules.permissions.routes.schemas import (
    PermissionBundleResponse,
    RoleBundlesRequest,
    UpsertPermissionBundleRequest,
)
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode

router = APIRouter(prefix="/permission-bundles", tags=["permissions"])


def _to_response(view: PermissionGroupView) -> PermissionBundleResponse:
    return PermissionBundleResponse(
        id=view.id,
        slug=view.slug,
        service=view.service,
        name=view.name,
        description=view.description,
        is_active=view.is_active,
        permission_ids=list(view.permission_ids),
        permission_codes=list(view.permission_codes),
    )


@router.get("", response_model=list[PermissionBundleResponse])
@inject
async def list_bundles(
    service: str | None = None,
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSION_GROUPS_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    groups: PermissionGroupService = Depends(Provide[Container.permission_group_service]),
) -> list[PermissionBundleResponse]:
    async with uow_factory:
        views = await groups.list_groups(service=service.strip().lower() if service else None)
        return [_to_response(view) for view in views]


@router.put("", response_model=PermissionBundleResponse)
@inject
async def upsert_bundle(
    body: UpsertPermissionBundleRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSION_GROUPS_MANAGE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    groups: PermissionGroupService = Depends(Provide[Container.permission_group_service]),
) -> PermissionBundleResponse:
    async with uow_factory as uow:
        model = await groups.upsert_group(
            slug=body.slug,
            service=body.service,
            name=body.name,
            description=body.description,
            permission_ids=frozenset(body.permission_ids),
        )
        group_id = model.id
        await uow.commit()

    async with uow_factory:
        views = await groups.list_groups()
        view = next(item for item in views if item.id == group_id)
        return _to_response(view)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_bundle(
    group_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.PERMISSION_GROUPS_MANAGE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    groups: PermissionGroupService = Depends(Provide[Container.permission_group_service]),
) -> None:
    async with uow_factory as uow:
        await groups.delete_group(group_id)
        await uow.commit()


@router.get("/roles/{role_id}", response_model=list[UUID])
@inject
async def role_bundles(
    role_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    groups: PermissionGroupService = Depends(Provide[Container.permission_group_service]),
) -> list[UUID]:
    async with uow_factory:
        return list(await groups.groups_for_role(role_id))


@router.put("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def replace_role_bundles(
    role_id: UUID,
    body: RoleBundlesRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.ROLES_ASSIGN)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    groups: PermissionGroupService = Depends(Provide[Container.permission_group_service]),
) -> None:
    async with uow_factory as uow:
        await groups.replace_role_groups(role_id=role_id, group_ids=frozenset(body.group_ids))
        await uow.commit()
