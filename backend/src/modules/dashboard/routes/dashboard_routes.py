"""Dashboard HTTP routes."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.modules.dashboard.dtos.dashboard_dtos import DashboardDto
from src.modules.dashboard.queries.dashboard_queries import GetDashboardQuery
from src.modules.dashboard.routes.schemas import (
    DashboardMenuItemResponse,
    DashboardResponse,
    DashboardWidgetResponse,
)
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import (
    get_current_user,
    require_any_permission,
)
from src.shared.infrastructure.security.permission_codes import PermissionCode

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_DASHBOARD_ACCESS = require_any_permission(
    PermissionCode.DASHBOARD_ADMIN,
    PermissionCode.DASHBOARD_MANAGER,
    PermissionCode.DASHBOARD_OPERATOR,
    PermissionCode.DASHBOARD_CLIENT,
    PermissionCode.DASHBOARD_VIEWER,
)


def _to_response(dto: DashboardDto) -> DashboardResponse:
    return DashboardResponse(
        user_id=dto.user_id,
        email=dto.email,
        full_name=dto.full_name,
        tenant_id=dto.tenant_id,
        tenant_slug=dto.tenant_slug,
        tenant_name=dto.tenant_name,
        role_names=list(dto.role_names),
        permissions=list(dto.permissions),
        menu=[
            DashboardMenuItemResponse(
                id=item.id,
                label=item.label,
                route=item.route,
                icon=item.icon,
                required_permission=item.required_permission,
            )
            for item in dto.menu
        ],
        widgets=[
            DashboardWidgetResponse(
                id=widget.id,
                title=widget.title,
                widget_type=widget.widget_type,
                data=widget.data,
            )
            for widget in dto.widgets
        ],
    )


@router.get("", response_model=DashboardResponse)
@inject
async def get_dashboard(
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    user: CurrentUser = Depends(_DASHBOARD_ACCESS),
) -> DashboardResponse:
    dto: DashboardDto = await query_bus.ask(
        GetDashboardQuery(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            tenant_slug=user.tenant_slug,
            tenant_name=user.tenant_name,
            role_ids=user.role_ids,
            role_names=user.role_names,
            permissions=user.permissions,
        )
    )
    return _to_response(dto)


@router.get("/me", response_model=DashboardResponse)
@inject
async def get_my_dashboard(
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    user: CurrentUser = Depends(get_current_user),
) -> DashboardResponse:
    """Authenticated users always get a composed dashboard (may be empty)."""
    dto: DashboardDto = await query_bus.ask(
        GetDashboardQuery(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            tenant_slug=user.tenant_slug,
            tenant_name=user.tenant_name,
            role_ids=user.role_ids,
            role_names=user.role_names,
            permissions=user.permissions,
        )
    )
    return _to_response(dto)
