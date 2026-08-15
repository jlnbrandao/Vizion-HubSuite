"""Declarative navigation catalog.

The shell menu is data, not code: each service declares its entries here with the
permission that unlocks them. `NavigationService` filters the catalog per request,
so the SPA renders whatever it receives and never re-implements the rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.infrastructure.security.permission_codes import (
    SERVICE_IAM,
    SERVICE_INTEGRATION,
    SERVICE_PLATFORM,
    PermissionCode,
)

GROUP_OVERVIEW = "overview"
GROUP_ADMINISTRATION = "administration"
GROUP_SECURITY = "security"
GROUP_PLATFORM = "platform"
GROUP_WORKSPACE = "workspace"
GROUP_ACCOUNT = "account"


@dataclass(frozen=True, slots=True)
class NavItem:
    id: str
    label: str
    icon: str
    route: str
    group: str
    #: Service that owns the entry; None means the shell itself.
    service: str | None = None
    #: Permission required to see it; None means any authenticated user.
    permission: str | None = None
    #: Alternative codes: holding any one of them is enough.
    permission_any: tuple[str, ...] = ()
    #: Also offered in the compact top navigation.
    quick: bool = False


NAVIGATION_CATALOG: tuple[NavItem, ...] = (
    NavItem(
        id="admin-overview",
        label="Administration",
        icon="admin_panel_settings",
        route="/admin",
        group=GROUP_ADMINISTRATION,
        permission=PermissionCode.DASHBOARD_ADMIN,
        quick=True,
    ),
    NavItem(
        id="admin-users",
        label="Users",
        icon="people",
        route="/users",
        group=GROUP_ADMINISTRATION,
        service=SERVICE_IAM,
        permission=PermissionCode.USERS_READ,
        quick=True,
    ),
    NavItem(
        id="admin-roles",
        label="Roles",
        icon="shield",
        route="/roles",
        group=GROUP_ADMINISTRATION,
        service=SERVICE_IAM,
        permission=PermissionCode.ROLES_READ,
        quick=True,
    ),
    NavItem(
        id="admin-permissions",
        label="Permissions",
        icon="key",
        route="/permissions",
        group=GROUP_ADMINISTRATION,
        service=SERVICE_IAM,
        permission=PermissionCode.PERMISSIONS_READ,
        quick=True,
    ),
    NavItem(
        id="iam-audit",
        label="Audit",
        icon="policy",
        route="/iam/audit",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.AUDIT_READ,
    ),
    NavItem(
        id="iam-policies",
        label="Access policies",
        icon="rule",
        route="/iam/policies",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.POLICIES_READ,
    ),
    NavItem(
        id="iam-acls",
        label="Resource ACLs",
        icon="lock_person",
        route="/iam/acls",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.ACL_READ,
    ),
    NavItem(
        id="iam-oauth-clients",
        label="OAuth clients",
        icon="apps",
        route="/iam/oauth-clients",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.OAUTH_CLIENTS_READ,
    ),
    NavItem(
        id="iam-federation",
        label="Federation / SSO",
        icon="login",
        route="/iam/federation",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.FEDERATION_READ,
    ),
    NavItem(
        id="iam-api-keys",
        label="API keys",
        icon="vpn_key",
        route="/iam/api-keys",
        group=GROUP_SECURITY,
        service=SERVICE_IAM,
        permission=PermissionCode.API_KEYS_READ,
    ),
    NavItem(
        id="platform-tenants",
        label="Tenants",
        icon="domain",
        route="/tenants",
        group=GROUP_PLATFORM,
        service=SERVICE_PLATFORM,
        permission=PermissionCode.TENANTS_READ,
        quick=True,
    ),
    NavItem(
        id="platform-services",
        label="Service entitlements",
        icon="widgets",
        route="/platform/services",
        group=GROUP_PLATFORM,
        service=SERVICE_PLATFORM,
        permission=PermissionCode.SERVICES_READ,
    ),
    NavItem(
        id="platform-usage",
        label="Usage",
        icon="query_stats",
        route="/usage",
        group=GROUP_PLATFORM,
        service=SERVICE_PLATFORM,
        # Tenant admins see their own consumption; the platform sees every tenant.
        permission_any=(PermissionCode.USAGE_READ, PermissionCode.USAGE_READ_ALL),
    ),
    NavItem(
        id="integration-hub",
        label="Integrations",
        icon="hub",
        route="/integrations",
        group=GROUP_PLATFORM,
        service=SERVICE_INTEGRATION,
        permission=PermissionCode.INTEGRATION_READ,
    ),
    NavItem(
        id="manager-indicators",
        label="Indicators",
        icon="insights",
        route="/reports/indicators",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_MANAGER,
        quick=True,
    ),
    NavItem(
        id="manager-reports",
        label="Reports",
        icon="description",
        route="/reports",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_MANAGER,
        quick=True,
    ),
    NavItem(
        id="operator-operations",
        label="Operations",
        icon="task_alt",
        route="/operations/today",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_OPERATOR,
        quick=True,
    ),
    NavItem(
        id="client-map",
        label="Map",
        icon="map",
        route="/main",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_CLIENT,
        quick=True,
    ),
    NavItem(
        id="client-profile",
        label="My data",
        icon="person",
        route="/me",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_CLIENT,
        quick=True,
    ),
    NavItem(
        id="viewer-readonly",
        label="Read-only view",
        icon="visibility",
        route="/dashboard/readonly",
        group=GROUP_WORKSPACE,
        permission=PermissionCode.DASHBOARD_VIEWER,
        quick=True,
    ),
    NavItem(
        id="account-profile",
        label="My account",
        icon="manage_accounts",
        route="/account/profile",
        group=GROUP_ACCOUNT,
    ),
    NavItem(
        id="account-sessions",
        label="My sessions",
        icon="devices",
        route="/iam/sessions",
        group=GROUP_ACCOUNT,
    ),
    NavItem(
        id="account-mfa",
        label="MFA setup",
        icon="phonelink_lock",
        route="/iam/mfa",
        group=GROUP_ACCOUNT,
    ),
)
