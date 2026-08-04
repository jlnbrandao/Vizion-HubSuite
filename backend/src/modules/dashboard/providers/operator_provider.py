"""OPERATOR dashboard section — day-to-day operations."""

from __future__ import annotations

from datetime import UTC, datetime

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class OperatorDashboardProvider(DashboardSectionProvider):
    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_OPERATOR

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="operator-ops",
                label="Operações do dia",
                route="/operations/today",
                icon="task_alt",
                required_permission=PermissionCode.DASHBOARD_OPERATOR,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        today = datetime.now(UTC).date().isoformat()
        return [
            DashboardWidget(
                id="operator-today",
                title="Operações do dia",
                widget_type="operations",
                data={
                    "date": today,
                    "pending_tasks": 14,
                    "completed_tasks": 9,
                    "queue": [
                        {"id": "op-1", "label": "Conferir remessa #4412"},
                        {"id": "op-2", "label": "Atualizar status pedido #8891"},
                        {"id": "op-3", "label": "Registrar ocorrência #120"},
                    ],
                },
            ),
        ]
