"""Static validation of the seed role → permission map."""

from __future__ import annotations

from scripts.seed import ROLE_PERMISSIONS, validate_role_permissions_map
from src.shared.infrastructure.security.permission_codes import PermissionCode


def test_role_permissions_map_is_valid() -> None:
    validate_role_permissions_map()


def test_admin_has_every_permission_code() -> None:
    assert ROLE_PERMISSIONS["ADMIN"] == frozenset(PermissionCode.all_codes())


def test_expected_roles_present() -> None:
    assert set(ROLE_PERMISSIONS) == {"ADMIN", "MANAGER", "OPERATOR", "CLIENT", "VIEWER"}
