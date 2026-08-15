"""VIEWER dashboard section — read-only overview."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class ViewerDashboardProvider(DashboardSectionProvider):
    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_VIEWER

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        return [
            DashboardWidget(
                id="viewer-readonly",
                title="Read only",
                widget_type="readonly",
                data={
                    "message": "You have read-only access to the system.",
                    "allowed_actions": ["view"],
                    "denied_actions": ["create", "edit", "delete"],
                },
            ),
        ]
