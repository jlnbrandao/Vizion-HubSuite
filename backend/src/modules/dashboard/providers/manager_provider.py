"""MANAGER dashboard section — company indicators and reports."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class ManagerDashboardProvider(DashboardSectionProvider):
    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_MANAGER

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="manager-indicators",
                label="Indicadores da empresa",
                route="/reports/indicators",
                icon="insights",
                required_permission=PermissionCode.DASHBOARD_MANAGER,
            ),
            DashboardMenuItem(
                id="manager-reports",
                label="Relatórios",
                route="/reports",
                icon="description",
                required_permission=PermissionCode.DASHBOARD_MANAGER,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        return [
            DashboardWidget(
                id="manager-kpis",
                title="Indicadores da empresa",
                widget_type="indicators",
                data={
                    "revenue_mtd": 128450.75,
                    "orders_mtd": 842,
                    "conversion_rate": 0.037,
                    "nps": 72,
                },
            ),
            DashboardWidget(
                id="manager-reports",
                title="Relatórios",
                widget_type="actions",
                data={
                    "reports": [
                        {"id": "sales-weekly", "label": "Vendas semanais"},
                        {"id": "pipeline", "label": "Pipeline comercial"},
                        {"id": "headcount", "label": "Headcount"},
                    ]
                },
            ),
        ]
