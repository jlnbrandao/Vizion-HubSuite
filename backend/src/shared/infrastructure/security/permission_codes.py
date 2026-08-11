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
            }
        )

    @classmethod
    def admin_role_codes(cls) -> frozenset[str]:
        """Default ADMIN role: identity/RBAC CRUD + admin dashboard only."""
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
)

_CATALOG_BY_CODE: dict[str, PermissionDefinition] = {
    item.code: item for item in PERMISSION_CATALOG
}
