"""Navigation HTTP routes — the SPA shell menu, resolved server-side."""

from __future__ import annotations

from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.modules.navigation.service import NavigationService
from src.modules.services.service import ServiceCatalogService
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import get_current_user

router = APIRouter(prefix="/navigation", tags=["navigation"])

_service = NavigationService()


class NavigationItemResponse(BaseModel):
    id: str
    label: str
    icon: str
    route: str
    group: str
    service: str | None = None
    permission: str | None = None
    quick: bool = False


class NavigationResponse(BaseModel):
    home_route: str
    services: list[str]
    items: list[NavigationItemResponse]


@router.get("", response_model=NavigationResponse)
@inject
async def get_navigation(
    user: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    catalog: ServiceCatalogService = Depends(Provide[Container.service_catalog]),
) -> NavigationResponse:
    """Menu tree already filtered by entitlement and RBAC."""
    async with uow_factory:
        contracted = await catalog.entitled_namespaces(user.tenant_id)

    view = _service.resolve(user, contracted)
    return NavigationResponse(
        home_route=view.home_route,
        services=list(view.services),
        items=[
            NavigationItemResponse(
                id=item.id,
                label=item.label,
                icon=item.icon,
                route=item.route,
                group=item.group,
                service=item.service,
                permission=item.permission,
                quick=item.quick,
            )
            for item in view.items
        ],
    )
