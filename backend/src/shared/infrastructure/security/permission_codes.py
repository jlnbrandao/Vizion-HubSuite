"""Canonical permission catalog — the single source of truth for RBAC codes.

Codes are namespaced as `service.resource.action` (e.g. `iam.users.create`). Every
entry also carries the legacy `resource.action` alias so existing routes, seeds and
tokens keep working until the aliases are dropped in an explicit later step.

Routes and the frontend reference these constants — never ad-hoc strings. The
frontend copy in `frontend/src/constants/permissions.ts` is generated from here by
`scripts/generate_frontend_permissions.py`; do not edit it by hand.
"""

from __future__ import annotations

from dataclasses import dataclass

SERVICE_IAM = "iam"
SERVICE_PLATFORM = "platform"
SERVICE_INTEGRATION = "integration"
SERVICE_BILLING = "billing"

#: Stable resource → service map. A resource may only ever move service with a
#: migration, since it changes the canonical code.
SERVICE_BY_RESOURCE: dict[str, str] = {
    "users": SERVICE_IAM,
    "roles": SERVICE_IAM,
    "permissions": SERVICE_IAM,
    "permission_groups": SERVICE_IAM,
    "dashboard": SERVICE_IAM,
    "system": SERVICE_IAM,
    "audit": SERVICE_IAM,
    "sessions": SERVICE_IAM,
    "oauth_clients": SERVICE_IAM,
    "service_accounts": SERVICE_IAM,
    "api_keys": SERVICE_IAM,
    "federation": SERVICE_IAM,
    "policies": SERVICE_IAM,
    "acl": SERVICE_IAM,
    "scim": SERVICE_IAM,
    "tenants": SERVICE_PLATFORM,
    "services": SERVICE_PLATFORM,
    "usage": SERVICE_PLATFORM,
    "integration": SERVICE_INTEGRATION,
    "invoices": SERVICE_BILLING,
    "payments": SERVICE_BILLING,
    "payment_methods": SERVICE_BILLING,
    "billing_settings": SERVICE_BILLING,
}


def service_for_resource(resource: str) -> str:
    """Service that owns a resource. Unknown resources are a catalog bug."""
    try:
        return SERVICE_BY_RESOURCE[resource]
    except KeyError as exc:
        raise ValueError(
            f"Unknown permission resource '{resource}' — add it to SERVICE_BY_RESOURCE"
        ) from exc


class PermissionAction:
    """Standardized action verbs for permission codes.

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
    legacy_code: str
    service: str
    name: str
    description: str

    @property
    def resource(self) -> str:
        return self.legacy_code.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.legacy_code.split(".", 1)[1]

    @property
    def codes(self) -> tuple[str, ...]:
        """Canonical code plus its legacy alias."""
        return (self.code, self.legacy_code)


def _definition(legacy_code: str, name: str, description: str) -> PermissionDefinition:
    resource, action = legacy_code.split(".", 1)
    service = service_for_resource(resource)
    return PermissionDefinition(
        code=f"{service}.{resource}.{action}",
        legacy_code=legacy_code,
        service=service,
        name=name,
        description=description,
    )


class PermissionCode:
    """Legacy `resource.action` constants — still the form used by routes.

    Use `canonical()` when the namespaced form is needed, and `expand()` to build a
    set that satisfies both forms.
    """

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

    PERMISSION_GROUPS_READ = "permission_groups.read"
    PERMISSION_GROUPS_MANAGE = "permission_groups.manage"

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

    SERVICES_READ = "services.read"
    SERVICES_MANAGE = "services.manage"

    USAGE_READ = "usage.read"
    USAGE_READ_ALL = "usage.read_all"

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
    ACL_READ = "acl.read"
    ACL_GRANT = "acl.grant"
    ACL_REVOKE = "acl.revoke"

    # Integration hub
    INTEGRATION_READ = "integration.read"
    INTEGRATION_CREATE = "integration.create"
    INTEGRATION_UPDATE = "integration.update"
    INTEGRATION_DELETE = "integration.delete"
    INTEGRATION_TEST = "integration.test"
    INTEGRATION_SYNC = "integration.sync"
    INTEGRATION_LOGS_READ = "integration.read_logs"

    # Billing (product tenants only)
    INVOICES_READ = "invoices.read"
    INVOICES_EXPORT = "invoices.export"
    PAYMENTS_CREATE = "payments.create"
    PAYMENT_METHODS_READ = "payment_methods.read"
    PAYMENT_METHODS_MANAGE = "payment_methods.manage"
    BILLING_SETTINGS_READ = "billing_settings.read"
    BILLING_SETTINGS_UPDATE = "billing_settings.update"

    @classmethod
    def platform_only_codes(cls) -> frozenset[str]:
        """Codes that must not be granted inside ordinary tenant RBAC.

        Returns both the canonical and legacy form of each code so membership tests
        work no matter which shape the caller holds.
        """
        return _PLATFORM_ONLY_CODES

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
                cls.PERMISSION_GROUPS_READ,
                cls.PERMISSION_GROUPS_MANAGE,
                cls.DASHBOARD_ADMIN,
                cls.USAGE_READ,
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
                cls.ACL_READ,
                cls.ACL_GRANT,
                cls.ACL_REVOKE,
            }
        )

    @classmethod
    def all_codes(cls) -> tuple[str, ...]:
        """Legacy constants declared on this class."""
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
        """Look a definition up by either the canonical or the legacy code."""
        return _CATALOG_BY_CODE.get(code)

    @classmethod
    def canonical(cls, code: str) -> str:
        """Namespaced form of a code; unknown codes are returned unchanged."""
        definition = _CATALOG_BY_CODE.get(code)
        return definition.code if definition else code

    @classmethod
    def legacy(cls, code: str) -> str | None:
        definition = _CATALOG_BY_CODE.get(code)
        return definition.legacy_code if definition else None

    @classmethod
    def service_of(cls, code: str) -> str | None:
        """Service of a code: from the catalog, the namespace, or the resource map."""
        definition = _CATALOG_BY_CODE.get(code)
        if definition is not None:
            return definition.service
        parts = code.split(".")
        if len(parts) >= 3:
            return parts[0]
        if len(parts) == 2:
            return SERVICE_BY_RESOURCE.get(parts[0])
        return None

    @classmethod
    def aliases(cls, code: str) -> frozenset[str]:
        """Every accepted form of a code (canonical + legacy)."""
        definition = _CATALOG_BY_CODE.get(code)
        return frozenset(definition.codes) if definition else frozenset({code})

    @classmethod
    def expand(cls, codes: frozenset[str] | set[str] | tuple[str, ...]) -> frozenset[str]:
        """Add the missing alias for each code so both forms authorize equally."""
        expanded: set[str] = set()
        for code in codes:
            expanded.add(code)
            definition = _CATALOG_BY_CODE.get(code)
            if definition is not None:
                expanded.update(definition.codes)
        return frozenset(expanded)

    @classmethod
    def codes_for_service(cls, service: str) -> frozenset[str]:
        return frozenset(item.code for item in PERMISSION_CATALOG if item.service == service)

    @classmethod
    def known_codes(cls) -> frozenset[str]:
        """Every catalog code in both forms."""
        return frozenset(_CATALOG_BY_CODE)

    @classmethod
    def bundles(cls) -> tuple[PermissionBundleDefinition, ...]:
        return PERMISSION_BUNDLES

    @classmethod
    def bundle(cls, slug: str) -> PermissionBundleDefinition:
        try:
            return _BUNDLES_BY_SLUG[slug]
        except KeyError as exc:
            raise ValueError(f"Unknown permission bundle: {slug}") from exc


PERMISSION_CATALOG: tuple[PermissionDefinition, ...] = (
    _definition("users.create", "Create users", "Allows creating users"),
    _definition("users.read", "Read users", "Allows viewing users"),
    _definition("users.update", "Update users", "Allows editing users"),
    _definition("users.delete", "Delete users", "Allows deleting users"),
    _definition(
        "users.assign",
        "Assign user roles",
        "Allows assigning and removing user roles",
    ),
    _definition("roles.create", "Create roles", "Allows creating roles"),
    _definition("roles.read", "Read roles", "Allows viewing roles"),
    _definition("roles.update", "Update roles", "Allows editing roles"),
    _definition("roles.delete", "Delete roles", "Allows deleting roles"),
    _definition(
        "roles.assign",
        "Assign role permissions",
        "Allows assigning and removing role permissions",
    ),
    _definition("permissions.create", "Create permissions", "Allows creating permissions"),
    _definition("permissions.read", "Read permissions", "Allows viewing permissions"),
    _definition("permissions.update", "Update permissions", "Allows editing permissions"),
    _definition("permissions.delete", "Delete permissions", "Allows deleting permissions"),
    _definition(
        "permission_groups.read",
        "Read permission bundles",
        "Allows viewing permission bundles",
    ),
    _definition(
        "permission_groups.manage",
        "Manage permission bundles",
        "Allows creating bundles and composing roles from them",
    ),
    _definition(
        "dashboard.admin",
        "Dashboard admin",
        "Access to the admin dashboard section",
    ),
    _definition(
        "dashboard.manager",
        "Dashboard manager",
        "Access to the manager dashboard section",
    ),
    _definition(
        "dashboard.operator",
        "Dashboard operator",
        "Access to the operator dashboard section",
    ),
    _definition(
        "dashboard.client",
        "Dashboard client",
        "Access to the client dashboard section",
    ),
    _definition(
        "dashboard.viewer",
        "Dashboard viewer",
        "Access to the viewer dashboard section",
    ),
    _definition(
        "dashboard.platform",
        "Dashboard platform",
        "Access to the platform tenant administration section",
    ),
    _definition("system.settings", "System settings", "Allows managing system settings"),
    _definition("tenants.create", "Create tenants", "Allows creating tenants (platform)"),
    _definition("tenants.read", "Read tenants", "Allows listing tenants (platform)"),
    _definition("tenants.update", "Update tenants", "Allows renaming tenants (platform)"),
    _definition(
        "tenants.activate",
        "Activate tenants",
        "Allows activating tenants (platform)",
    ),
    _definition(
        "tenants.deactivate",
        "Deactivate tenants",
        "Allows suspending tenants (platform)",
    ),
    _definition(
        "services.read",
        "Read service catalog",
        "Allows listing Hub services and tenant entitlements",
    ),
    _definition(
        "services.manage",
        "Manage service entitlements",
        "Allows enabling, suspending and quoting services per tenant",
    ),
    _definition(
        "usage.read",
        "Read usage",
        "Allows viewing the own tenant's metered usage",
    ),
    _definition(
        "usage.read_all",
        "Read usage of every tenant",
        "Allows viewing metered usage across tenants (platform)",
    ),
    _definition("audit.read", "Read audit events", "Allows viewing the audit trail"),
    _definition("sessions.revoke", "Revoke sessions", "Allows revoking user sessions"),
    _definition(
        "oauth_clients.create",
        "Create OAuth clients",
        "Allows registering OAuth/OIDC clients",
    ),
    _definition(
        "oauth_clients.read",
        "Read OAuth clients",
        "Allows listing OAuth/OIDC clients",
    ),
    _definition(
        "oauth_clients.update",
        "Update OAuth clients",
        "Allows updating OAuth/OIDC clients",
    ),
    _definition(
        "oauth_clients.delete",
        "Delete OAuth clients",
        "Allows deleting OAuth/OIDC clients",
    ),
    _definition(
        "service_accounts.create",
        "Create service accounts",
        "Allows creating non-human identities",
    ),
    _definition(
        "service_accounts.read",
        "Read service accounts",
        "Allows listing service accounts",
    ),
    _definition(
        "service_accounts.update",
        "Update service accounts",
        "Allows updating service accounts",
    ),
    _definition(
        "service_accounts.delete",
        "Delete service accounts",
        "Allows deleting service accounts",
    ),
    _definition("api_keys.create", "Create API keys", "Allows issuing API keys"),
    _definition("api_keys.read", "Read API keys", "Allows listing API keys"),
    _definition("api_keys.delete", "Delete API keys", "Allows revoking API keys"),
    _definition(
        "federation.create",
        "Create identity providers",
        "Allows configuring SSO/federation IdPs",
    ),
    _definition(
        "federation.read",
        "Read identity providers",
        "Allows listing SSO/federation IdPs",
    ),
    _definition(
        "federation.update",
        "Update identity providers",
        "Allows updating SSO/federation IdPs",
    ),
    _definition(
        "federation.delete",
        "Delete identity providers",
        "Allows removing SSO/federation IdPs",
    ),
    _definition(
        "policies.create",
        "Create access policies",
        "Allows creating ABAC/auth policies",
    ),
    _definition(
        "policies.read",
        "Read access policies",
        "Allows viewing ABAC/auth policies",
    ),
    _definition(
        "policies.update",
        "Update access policies",
        "Allows updating ABAC/auth policies",
    ),
    _definition(
        "policies.delete",
        "Delete access policies",
        "Allows deleting ABAC/auth policies",
    ),
    _definition("scim.provision", "SCIM provision", "Allows SCIM user/group provisioning"),
    _definition(
        "acl.read",
        "Read resource ACLs",
        "Allows viewing per-resource access control entries",
    ),
    _definition(
        "acl.grant",
        "Grant resource ACLs",
        "Allows creating per-resource allow/deny entries",
    ),
    _definition(
        "acl.revoke",
        "Revoke resource ACLs",
        "Allows removing per-resource access control entries",
    ),
    _definition("integration.read", "Read integrations", "Allows viewing integrations"),
    _definition("integration.create", "Create integrations", "Allows creating integrations"),
    _definition("integration.update", "Update integrations", "Allows updating integrations"),
    _definition("integration.delete", "Delete integrations", "Allows deleting integrations"),
    _definition(
        "integration.test",
        "Test integrations",
        "Allows testing integration connections",
    ),
    _definition(
        "integration.sync",
        "Sync integrations",
        "Allows running integration synchronization",
    ),
    _definition(
        "integration.read_logs",
        "Read integration logs",
        "Allows viewing integration sync/test logs",
    ),
    _definition(
        "invoices.read",
        "Read invoices",
        "Allows viewing invoices and the billing overview",
    ),
    _definition("invoices.export", "Export invoices", "Allows downloading invoice documents"),
    _definition("payments.create", "Create payments", "Allows paying an invoice"),
    _definition(
        "payment_methods.read",
        "Read payment methods",
        "Allows listing saved payment methods",
    ),
    _definition(
        "payment_methods.manage",
        "Manage payment methods",
        "Allows adding and updating payment methods",
    ),
    _definition(
        "billing_settings.read",
        "Read billing settings",
        "Allows viewing the billing profile and cycle",
    ),
    _definition(
        "billing_settings.update",
        "Update billing settings",
        "Allows editing the billing profile, cycle and promo codes",
    ),
)

@dataclass(frozen=True, slots=True)
class PermissionBundleDefinition:
    """Seeded bundle: a named set of codes inside one service."""

    slug: str
    service: str
    name: str
    description: str
    legacy_codes: tuple[str, ...]

    @property
    def codes(self) -> tuple[str, ...]:
        """Canonical codes of the bundle members."""
        return tuple(PermissionCode.canonical(code) for code in self.legacy_codes)


def _bundle(
    slug: str,
    name: str,
    description: str,
    legacy_codes: frozenset[str] | set[str] | tuple[str, ...],
) -> PermissionBundleDefinition:
    service = slug.split(".", 1)[0]
    return PermissionBundleDefinition(
        slug=slug,
        service=service,
        name=name,
        description=description,
        legacy_codes=tuple(sorted(legacy_codes)),
    )


_CATALOG_BY_CODE: dict[str, PermissionDefinition] = {}
for _item in PERMISSION_CATALOG:
    _CATALOG_BY_CODE[_item.code] = _item
    _CATALOG_BY_CODE[_item.legacy_code] = _item

_PLATFORM_ONLY_LEGACY: frozenset[str] = frozenset(
    {
        PermissionCode.DASHBOARD_PLATFORM,
        PermissionCode.SYSTEM_SETTINGS,
        PermissionCode.TENANTS_CREATE,
        PermissionCode.TENANTS_READ,
        PermissionCode.TENANTS_UPDATE,
        PermissionCode.TENANTS_ACTIVATE,
        PermissionCode.TENANTS_DEACTIVATE,
        PermissionCode.SERVICES_READ,
        PermissionCode.SERVICES_MANAGE,
        PermissionCode.USAGE_READ_ALL,
        PermissionCode.INTEGRATION_READ,
        PermissionCode.INTEGRATION_CREATE,
        PermissionCode.INTEGRATION_UPDATE,
        PermissionCode.INTEGRATION_DELETE,
        PermissionCode.INTEGRATION_TEST,
        PermissionCode.INTEGRATION_SYNC,
        PermissionCode.INTEGRATION_LOGS_READ,
    }
)

_PLATFORM_ONLY_CODES: frozenset[str] = frozenset(
    code
    for legacy in _PLATFORM_ONLY_LEGACY
    for code in (_CATALOG_BY_CODE[legacy].codes if legacy in _CATALOG_BY_CODE else (legacy,))
)

#: Seeded bundles. Roles compose these instead of enumerating dozens of codes;
#: `role_permissions` stays available for fine-grained exceptions.
PERMISSION_BUNDLES: tuple[PermissionBundleDefinition, ...] = (
    _bundle(
        "iam.admin",
        "IAM administration",
        "Identity, RBAC and IAM platform administration",
        PermissionCode.admin_role_codes(),
    ),
    _bundle(
        "iam.manager",
        "IAM manager",
        "User oversight and read-only RBAC",
        {
            PermissionCode.USERS_READ,
            PermissionCode.USERS_UPDATE,
            PermissionCode.ROLES_READ,
            PermissionCode.PERMISSIONS_READ,
            PermissionCode.DASHBOARD_MANAGER,
        },
    ),
    _bundle(
        "iam.operator",
        "IAM operator",
        "Day-to-day operations",
        {PermissionCode.USERS_READ, PermissionCode.DASHBOARD_OPERATOR},
    ),
    _bundle(
        "iam.client",
        "IAM client",
        "Own profile access only",
        {PermissionCode.DASHBOARD_CLIENT},
    ),
    _bundle(
        "iam.viewer",
        "IAM viewer",
        "Read-only system overview",
        {
            PermissionCode.USERS_READ,
            PermissionCode.ROLES_READ,
            PermissionCode.PERMISSIONS_READ,
            PermissionCode.DASHBOARD_VIEWER,
        },
    ),
    _bundle(
        "platform.admin",
        "Platform administration",
        "Cross-tenant administration and system settings",
        {
            PermissionCode.DASHBOARD_PLATFORM,
            PermissionCode.SYSTEM_SETTINGS,
            PermissionCode.TENANTS_CREATE,
            PermissionCode.TENANTS_READ,
            PermissionCode.TENANTS_UPDATE,
            PermissionCode.TENANTS_ACTIVATE,
            PermissionCode.TENANTS_DEACTIVATE,
            PermissionCode.SERVICES_READ,
            PermissionCode.SERVICES_MANAGE,
            # Own-tenant `usage.read` is a tenant-admin code; the platform reads
            # every tenant through `usage.read_all`.
            PermissionCode.USAGE_READ_ALL,
        },
    ),
    _bundle(
        "integration.admin",
        "Integration administration",
        "Full control over the integration hub",
        {
            PermissionCode.INTEGRATION_READ,
            PermissionCode.INTEGRATION_CREATE,
            PermissionCode.INTEGRATION_UPDATE,
            PermissionCode.INTEGRATION_DELETE,
            PermissionCode.INTEGRATION_TEST,
            PermissionCode.INTEGRATION_SYNC,
            PermissionCode.INTEGRATION_LOGS_READ,
        },
    ),
    _bundle(
        "billing.admin",
        "Billing administration",
        "Full control over tenant billing, invoices and payments",
        {
            PermissionCode.INVOICES_READ,
            PermissionCode.INVOICES_EXPORT,
            PermissionCode.PAYMENTS_CREATE,
            PermissionCode.PAYMENT_METHODS_READ,
            PermissionCode.PAYMENT_METHODS_MANAGE,
            PermissionCode.BILLING_SETTINGS_READ,
            PermissionCode.BILLING_SETTINGS_UPDATE,
        },
    ),
    _bundle(
        "billing.manager",
        "Billing manager",
        "Read invoices, payment methods and billing settings",
        {
            PermissionCode.INVOICES_READ,
            PermissionCode.INVOICES_EXPORT,
            PermissionCode.PAYMENT_METHODS_READ,
            PermissionCode.BILLING_SETTINGS_READ,
        },
    ),
)

_BUNDLES_BY_SLUG: dict[str, PermissionBundleDefinition] = {
    bundle.slug: bundle for bundle in PERMISSION_BUNDLES
}
