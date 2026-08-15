"""PLATFORM dashboard section — cross-tenant catalog administration."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.modules.tenants.queries.tenant_queries import ListTenantsQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass


class PlatformDashboardProvider(DashboardSectionProvider):
    def __init__(self, query_bus: QueryBus) -> None:
        self._query_bus = query_bus

    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_PLATFORM

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        token = bind_rls_bypass(True)
        try:
            tenants = await self._query_bus.ask(ListTenantsQuery())
            active = sum(1 for tenant in tenants if tenant.is_active)
        finally:
            unbind_rls_bypass(token)

        return [
            DashboardWidget(
                id="platform-tenant-stats",
                title="Tenant catalog",
                widget_type="stats",
                data={
                    "tenants_total": len(tenants),
                    "tenants_active": active,
                    "tenants_inactive": len(tenants) - active,
                },
            ),
            DashboardWidget(
                id="platform-tenant-actions",
                title="Tenants",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Manage tenants", "route": "/tenants"},
                        {"label": "Create tenant", "route": "/tenants?create=1"},
                    ]
                },
            ),
        ]
