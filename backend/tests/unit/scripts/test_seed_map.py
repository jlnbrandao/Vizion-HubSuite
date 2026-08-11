"""Static validation of the seed role → permission map."""

from __future__ import annotations

from scripts.seed import (
    ADMIN_PERMISSIONS,
    FORBIDDEN_FOR_ADMIN,
    ROLE_PERMISSIONS,
    validate_role_permissions_map,
)
from src.shared.infrastructure.security.permission_codes import PermissionCode


def test_role_permissions_map_is_valid() -> None:
    validate_role_permissions_map()


def test_admin_has_rbac_crud_only() -> None:
    assert ROLE_PERMISSIONS["ADMIN"] == ADMIN_PERMISSIONS
    assert ROLE_PERMISSIONS["ADMIN"].isdisjoint(FORBIDDEN_FOR_ADMIN)
    assert PermissionCode.USERS_CREATE in ROLE_PERMISSIONS["ADMIN"]
    assert PermissionCode.ROLES_CREATE in ROLE_PERMISSIONS["ADMIN"]
    assert PermissionCode.PERMISSIONS_CREATE in ROLE_PERMISSIONS["ADMIN"]
    assert PermissionCode.DASHBOARD_ADMIN in ROLE_PERMISSIONS["ADMIN"]
    assert PermissionCode.DASHBOARD_MANAGER not in ROLE_PERMISSIONS["ADMIN"]
    assert PermissionCode.SYSTEM_SETTINGS not in ROLE_PERMISSIONS["ADMIN"]


def test_expected_roles_present() -> None:
    assert set(ROLE_PERMISSIONS) == {"ADMIN", "MANAGER", "OPERATOR", "CLIENT", "VIEWER"}


def test_platform_permissions_are_forbidden_for_admin() -> None:
    assert PermissionCode.platform_only_codes().issubset(FORBIDDEN_FOR_ADMIN)
    assert ROLE_PERMISSIONS["ADMIN"].isdisjoint(PermissionCode.platform_only_codes())
