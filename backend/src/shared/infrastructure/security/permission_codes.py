"""Canonical permission codes used by RBAC (resource.action).

Routes and frontend should reference these constants — never hardcode strings ad hoc.

Besides the code string, each catalog entry carries metadata (resource, action, name,
description) so UIs can list by resource, filter by action, and render labels.
"""

from __future__ import annotations

from dataclasses import dataclass


class PermissionAction:
    """Standardized action verbs for `resource.action` codes.

    Prefer these bare verbs. The resource already scopes meaning
    (e.g. `users.assign` vs `roles.assign`).
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    MANAGE = "manage"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    CANCEL = "cancel"
    EXECUTE = "execute"
    ASSIGN = "assign"
    LINK = "link"
    UNLINK = "unlink"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        )


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    """Catalog metadata for a permission code."""

    code: str
    name: str
    description: str

    @property
    def resource(self) -> str:
        return self.code.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.code.split(".", 1)[1]


class PermissionCode:
    USERS_CREATE = "users.create"
    USERS_READ = "users.read"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"
    USERS_ASSIGN = "users.assign"

    ROLES_CREATE = "roles.create"
    ROLES_READ = "roles.read"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    ROLES_ASSIGN = "roles.assign"

    PERMISSIONS_CREATE = "permissions.create"
    PERMISSIONS_READ = "permissions.read"
    PERMISSIONS_UPDATE = "permissions.update"
    PERMISSIONS_DELETE = "permissions.delete"

    DASHBOARD_ADMIN = "dashboard.admin"
    DASHBOARD_MANAGER = "dashboard.manager"
    DASHBOARD_OPERATOR = "dashboard.operator"
    DASHBOARD_CLIENT = "dashboard.client"
    DASHBOARD_VIEWER = "dashboard.viewer"
    DASHBOARD_PLATFORM = "dashboard.platform"

    SYSTEM_SETTINGS = "system.settings"

    TENANTS_CREATE = "tenants.create"
    TENANTS_READ = "tenants.read"
    TENANTS_UPDATE = "tenants.update"
    TENANTS_ACTIVATE = "tenants.activate"
    TENANTS_DEACTIVATE = "tenants.deactivate"

    # IAM platform
    AUDIT_READ = "audit.read"
    SESSIONS_REVOKE = "sessions.revoke"
    OAUTH_CLIENTS_CREATE = "oauth_clients.create"
    OAUTH_CLIENTS_READ = "oauth_clients.read"
    OAUTH_CLIENTS_UPDATE = "oauth_clients.update"
    OAUTH_CLIENTS_DELETE = "oauth_clients.delete"
    SERVICE_ACCOUNTS_CREATE = "service_accounts.create"
    SERVICE_ACCOUNTS_READ = "service_accounts.read"
    SERVICE_ACCOUNTS_UPDATE = "service_accounts.update"
    SERVICE_ACCOUNTS_DELETE = "service_accounts.delete"
    API_KEYS_CREATE = "api_keys.create"
    API_KEYS_READ = "api_keys.read"
    API_KEYS_DELETE = "api_keys.delete"
    FEDERATION_CREATE = "federation.create"
    FEDERATION_READ = "federation.read"
    FEDERATION_UPDATE = "federation.update"
    FEDERATION_DELETE = "federation.delete"
    POLICIES_CREATE = "policies.create"
    POLICIES_READ = "policies.read"
    POLICIES_UPDATE = "policies.update"
    POLICIES_DELETE = "policies.delete"
    SCIM_PROVISION = "scim.provision"

    # Integration hub
    INTEGRATION_READ = "integration.read"
    INTEGRATION_CREATE = "integration.create"
    INTEGRATION_UPDATE = "integration.update"
    INTEGRATION_DELETE = "integration.delete"
    INTEGRATION_TEST = "integration.test"
    INTEGRATION_SYNC = "integration.sync"
    INTEGRATION_LOGS_READ = "integration.read_logs"

    @classmethod
    def platform_only_codes(cls) -> frozenset[str]:
        """Codes that must not be granted inside ordinary tenant RBAC."""
        return frozenset(
            {
                cls.DASHBOARD_PLATFORM,
                cls.SYSTEM_SETTINGS,
                cls.TENANTS_CREATE,
                cls.TENANTS_READ,
                cls.TENANTS_UPDATE,
                cls.TENANTS_ACTIVATE,
                cls.TENANTS_DEACTIVATE,
                cls.INTEGRATION_READ,
                cls.INTEGRATION_CREATE,
                cls.INTEGRATION_UPDATE,
                cls.INTEGRATION_DELETE,
                cls.INTEGRATION_TEST,
                cls.INTEGRATION_SYNC,
                cls.INTEGRATION_LOGS_READ,
            }
        )

    @classmethod
    def admin_role_codes(cls) -> frozenset[str]:
        """Default ADMIN role: identity/RBAC CRUD + IAM admin + admin dashboard."""
        return frozenset(
            {
                cls.USERS_CREATE,
                cls.USERS_READ,
                cls.USERS_UPDATE,
                cls.USERS_DELETE,
                cls.USERS_ASSIGN,
                cls.ROLES_CREATE,
                cls.ROLES_READ,
                cls.ROLES_UPDATE,
                cls.ROLES_DELETE,
                cls.ROLES_ASSIGN,
                cls.PERMISSIONS_CREATE,
                cls.PERMISSIONS_READ,
                cls.PERMISSIONS_UPDATE,
                cls.PERMISSIONS_DELETE,
                cls.DASHBOARD_ADMIN,
                cls.AUDIT_READ,
                cls.SESSIONS_REVOKE,
                cls.OAUTH_CLIENTS_CREATE,
                cls.OAUTH_CLIENTS_READ,
                cls.OAUTH_CLIENTS_UPDATE,
                cls.OAUTH_CLIENTS_DELETE,
                cls.SERVICE_ACCOUNTS_CREATE,
                cls.SERVICE_ACCOUNTS_READ,
                cls.SERVICE_ACCOUNTS_UPDATE,
                cls.SERVICE_ACCOUNTS_DELETE,
                cls.API_KEYS_CREATE,
                cls.API_KEYS_READ,
                cls.API_KEYS_DELETE,
                cls.FEDERATION_CREATE,
                cls.FEDERATION_READ,
                cls.FEDERATION_UPDATE,
                cls.FEDERATION_DELETE,
                cls.POLICIES_CREATE,
                cls.POLICIES_READ,
                cls.POLICIES_UPDATE,
                cls.POLICIES_DELETE,
                cls.SCIM_PROVISION,
            }
        )

    @classmethod
    def all_codes(cls) -> tuple[str, ...]:
        return tuple(
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        )

    @classmethod
    def catalog(cls) -> tuple[PermissionDefinition, ...]:
        return PERMISSION_CATALOG

    @classmethod
    def definition_for(cls, code: str) -> PermissionDefinition | None:
        return _CATALOG_BY_CODE.get(code)


PERMISSION_CATALOG: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        code=PermissionCode.USERS_CREATE,
        name="Create users",
        description="Allows creating users",
    ),
    PermissionDefinition(
        code=PermissionCode.USERS_READ,
        name="Read users",
        description="Allows viewing users",
    ),
    PermissionDefinition(
        code=PermissionCode.USERS_UPDATE,
        name="Update users",
        description="Allows editing users",
    ),
    PermissionDefinition(
        code=PermissionCode.USERS_DELETE,
        name="Delete users",
        description="Allows deleting users",
    ),
    PermissionDefinition(
        code=PermissionCode.USERS_ASSIGN,
        name="Assign user roles",
        description="Allows assigning and removing user roles",
    ),
    PermissionDefinition(
        code=PermissionCode.ROLES_CREATE,
        name="Create roles",
        description="Allows creating roles",
    ),
    PermissionDefinition(
        code=PermissionCode.ROLES_READ,
        name="Read roles",
        description="Allows viewing roles",
    ),
    PermissionDefinition(
        code=PermissionCode.ROLES_UPDATE,
        name="Update roles",
        description="Allows editing roles",
    ),
    PermissionDefinition(
        code=PermissionCode.ROLES_DELETE,
        name="Delete roles",
        description="Allows deleting roles",
    ),
    PermissionDefinition(
        code=PermissionCode.ROLES_ASSIGN,
        name="Assign role permissions",
        description="Allows assigning and removing role permissions",
    ),
    PermissionDefinition(
        code=PermissionCode.PERMISSIONS_CREATE,
        name="Create permissions",
        description="Allows creating permissions",
    ),
    PermissionDefinition(
        code=PermissionCode.PERMISSIONS_READ,
        name="Read permissions",
        description="Allows viewing permissions",
    ),
    PermissionDefinition(
        code=PermissionCode.PERMISSIONS_UPDATE,
        name="Update permissions",
        description="Allows editing permissions",
    ),
    PermissionDefinition(
        code=PermissionCode.PERMISSIONS_DELETE,
        name="Delete permissions",
        description="Allows deleting permissions",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_ADMIN,
        name="Dashboard admin",
        description="Access to the admin dashboard section",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_MANAGER,
        name="Dashboard manager",
        description="Access to the manager dashboard section",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_OPERATOR,
        name="Dashboard operator",
        description="Access to the operator dashboard section",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_CLIENT,
        name="Dashboard client",
        description="Access to the client dashboard section",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_VIEWER,
        name="Dashboard viewer",
        description="Access to the viewer dashboard section",
    ),
    PermissionDefinition(
        code=PermissionCode.DASHBOARD_PLATFORM,
        name="Dashboard platform",
        description="Access to the platform tenant administration section",
    ),
    PermissionDefinition(
        code=PermissionCode.SYSTEM_SETTINGS,
        name="System settings",
        description="Allows managing system settings",
    ),
    PermissionDefinition(
        code=PermissionCode.TENANTS_CREATE,
        name="Create tenants",
        description="Allows creating tenants (platform)",
    ),
    PermissionDefinition(
        code=PermissionCode.TENANTS_READ,
        name="Read tenants",
        description="Allows listing tenants (platform)",
    ),
    PermissionDefinition(
        code=PermissionCode.TENANTS_UPDATE,
        name="Update tenants",
        description="Allows renaming tenants (platform)",
    ),
    PermissionDefinition(
        code=PermissionCode.TENANTS_ACTIVATE,
        name="Activate tenants",
        description="Allows activating tenants (platform)",
    ),
    PermissionDefinition(
        code=PermissionCode.TENANTS_DEACTIVATE,
        name="Deactivate tenants",
        description="Allows suspending tenants (platform)",
    ),
    PermissionDefinition(
        code=PermissionCode.AUDIT_READ,
        name="Read audit events",
        description="Allows viewing the audit trail",
    ),
    PermissionDefinition(
        code=PermissionCode.SESSIONS_REVOKE,
        name="Revoke sessions",
        description="Allows revoking user sessions",
    ),
    PermissionDefinition(
        code=PermissionCode.OAUTH_CLIENTS_CREATE,
        name="Create OAuth clients",
        description="Allows registering OAuth/OIDC clients",
    ),
    PermissionDefinition(
        code=PermissionCode.OAUTH_CLIENTS_READ,
        name="Read OAuth clients",
        description="Allows listing OAuth/OIDC clients",
    ),
    PermissionDefinition(
        code=PermissionCode.OAUTH_CLIENTS_UPDATE,
        name="Update OAuth clients",
        description="Allows updating OAuth/OIDC clients",
    ),
    PermissionDefinition(
        code=PermissionCode.OAUTH_CLIENTS_DELETE,
        name="Delete OAuth clients",
        description="Allows deleting OAuth/OIDC clients",
    ),
    PermissionDefinition(
        code=PermissionCode.SERVICE_ACCOUNTS_CREATE,
        name="Create service accounts",
        description="Allows creating non-human identities",
    ),
    PermissionDefinition(
        code=PermissionCode.SERVICE_ACCOUNTS_READ,
        name="Read service accounts",
        description="Allows listing service accounts",
    ),
    PermissionDefinition(
        code=PermissionCode.SERVICE_ACCOUNTS_UPDATE,
        name="Update service accounts",
        description="Allows updating service accounts",
    ),
    PermissionDefinition(
        code=PermissionCode.SERVICE_ACCOUNTS_DELETE,
        name="Delete service accounts",
        description="Allows deleting service accounts",
    ),
    PermissionDefinition(
        code=PermissionCode.API_KEYS_CREATE,
        name="Create API keys",
        description="Allows issuing API keys",
    ),
    PermissionDefinition(
        code=PermissionCode.API_KEYS_READ,
        name="Read API keys",
        description="Allows listing API keys",
    ),
    PermissionDefinition(
        code=PermissionCode.API_KEYS_DELETE,
        name="Delete API keys",
        description="Allows revoking API keys",
    ),
    PermissionDefinition(
        code=PermissionCode.FEDERATION_CREATE,
        name="Create identity providers",
        description="Allows configuring SSO/federation IdPs",
    ),
    PermissionDefinition(
        code=PermissionCode.FEDERATION_READ,
        name="Read identity providers",
        description="Allows listing SSO/federation IdPs",
    ),
    PermissionDefinition(
        code=PermissionCode.FEDERATION_UPDATE,
        name="Update identity providers",
        description="Allows updating SSO/federation IdPs",
    ),
    PermissionDefinition(
        code=PermissionCode.FEDERATION_DELETE,
        name="Delete identity providers",
        description="Allows removing SSO/federation IdPs",
    ),
    PermissionDefinition(
        code=PermissionCode.POLICIES_CREATE,
        name="Create access policies",
        description="Allows creating ABAC/auth policies",
    ),
    PermissionDefinition(
        code=PermissionCode.POLICIES_READ,
        name="Read access policies",
        description="Allows viewing ABAC/auth policies",
    ),
    PermissionDefinition(
        code=PermissionCode.POLICIES_UPDATE,
        name="Update access policies",
        description="Allows updating ABAC/auth policies",
    ),
    PermissionDefinition(
        code=PermissionCode.POLICIES_DELETE,
        name="Delete access policies",
        description="Allows deleting ABAC/auth policies",
    ),
    PermissionDefinition(
        code=PermissionCode.SCIM_PROVISION,
        name="SCIM provision",
        description="Allows SCIM user/group provisioning",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_READ,
        name="Read integrations",
        description="Allows viewing integrations",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_CREATE,
        name="Create integrations",
        description="Allows creating integrations",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_UPDATE,
        name="Update integrations",
        description="Allows updating integrations",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_DELETE,
        name="Delete integrations",
        description="Allows deleting integrations",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_TEST,
        name="Test integrations",
        description="Allows testing integration connections",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_SYNC,
        name="Sync integrations",
        description="Allows running integration synchronization",
    ),
    PermissionDefinition(
        code=PermissionCode.INTEGRATION_LOGS_READ,
        name="Read integration logs",
        description="Allows viewing integration sync/test logs",
    ),
)

_CATALOG_BY_CODE: dict[str, PermissionDefinition] = {
    item.code: item for item in PERMISSION_CATALOG
}
