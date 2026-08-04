"""VIEWER dashboard section — read-only overview."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class ViewerDashboardProvider(DashboardSectionProvider):
    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_VIEWER

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="viewer-overview",
                label="Visão somente leitura",
                route="/dashboard/readonly",
                icon="visibility",
                required_permission=PermissionCode.DASHBOARD_VIEWER,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        return [
            DashboardWidget(
                id="viewer-readonly",
                title="Somente leitura",
                widget_type="readonly",
                data={
                    "message": "Você possui acesso somente leitura ao sistema.",
                    "allowed_actions": ["visualizar"],
                    "denied_actions": ["criar", "editar", "excluir"],
                },
            ),
        ]
