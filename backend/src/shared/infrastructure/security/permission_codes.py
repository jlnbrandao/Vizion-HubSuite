"""Canonical permission codes used by RBAC (resource.action).

Routes and frontend should reference these constants — never hardcode strings ad hoc.
"""

from __future__ import annotations


class PermissionCode:
    USERS_CREATE = "users.create"
    USERS_READ = "users.read"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"
    USERS_ASSIGN_ROLES = "users.assign_roles"

    ROLES_CREATE = "roles.create"
    ROLES_READ = "roles.read"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    ROLES_ASSIGN_PERMISSIONS = "roles.assign_permissions"

    PERMISSIONS_CREATE = "permissions.create"
    PERMISSIONS_READ = "permissions.read"
    PERMISSIONS_UPDATE = "permissions.update"
    PERMISSIONS_DELETE = "permissions.delete"

    DASHBOARD_ADMIN = "dashboard.admin"
    DASHBOARD_MANAGER = "dashboard.manager"
    DASHBOARD_OPERATOR = "dashboard.operator"
    DASHBOARD_CLIENT = "dashboard.client"
    DASHBOARD_VIEWER = "dashboard.viewer"

    SYSTEM_SETTINGS = "system.settings"

    @classmethod
    def all_codes(cls) -> tuple[str, ...]:
        return tuple(
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        )
