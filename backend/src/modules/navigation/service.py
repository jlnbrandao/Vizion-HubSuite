"""Navigation resolution: entitlement + RBAC filtering of the shell menu."""

from __future__ import annotations

from dataclasses import dataclass

from src.modules.navigation.catalog import GROUP_OVERVIEW, NAVIGATION_CATALOG, NavItem
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.entitlements import entitled_services
from src.shared.infrastructure.security.permission_codes import PermissionCode

#: Holding any of these means the user gets the composed dashboard as home.
_COMPOSED_DASHBOARD_CODES: tuple[str, ...] = (
    PermissionCode.DASHBOARD_ADMIN,
    PermissionCode.DASHBOARD_MANAGER,
    PermissionCode.DASHBOARD_OPERATOR,
    PermissionCode.DASHBOARD_VIEWER,
    PermissionCode.DASHBOARD_PLATFORM,
)


@dataclass(frozen=True, slots=True)
class NavigationView:
    home_route: str
    items: tuple[NavItem, ...]
    services: tuple[str, ...]


class NavigationService:
    """Builds the menu the caller is allowed to see.

    Filtering order mirrors the authorization engine: a service the tenant has
    not contracted disappears entirely, then RBAC removes individual entries.
    """

    def __init__(self, catalog: tuple[NavItem, ...] = NAVIGATION_CATALOG) -> None:
        self._catalog = catalog

    def resolve(
        self,
        user: CurrentUser,
        contracted_services: frozenset[str] | None = None,
    ) -> NavigationView:
        services = entitled_services(user.permissions, contracted_services)
        client_home = user.has_permission(
            PermissionCode.DASHBOARD_CLIENT
        ) and not user.has_any_permission(*_COMPOSED_DASHBOARD_CODES)
        home_route = "/main" if client_home else "/dashboard"

        items: list[NavItem] = [
            NavItem(
                id="nav-home",
                label="Map" if client_home else "Dashboard",
                icon="map" if client_home else "dashboard",
                route=home_route,
                group=GROUP_OVERVIEW,
                quick=True,
            )
        ]
        for item in self._catalog:
            # The home entry already covers the client map.
            if client_home and item.route == home_route:
                continue
            if item.service is not None and item.service not in services:
                continue
            if item.permission is not None and not user.has_permission(item.permission):
                continue
            if item.permission_any and not user.has_any_permission(*item.permission_any):
                continue
            items.append(item)

        return NavigationView(
            home_route=home_route,
            items=tuple(items),
            services=tuple(sorted(services)),
        )
