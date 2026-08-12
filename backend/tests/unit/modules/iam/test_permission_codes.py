"""Permission catalog includes IAM codes."""

from __future__ import annotations

from src.shared.infrastructure.security.permission_codes import PermissionCode


def test_iam_permission_codes_in_catalog() -> None:
    codes = set(PermissionCode.all_codes())
    catalog = {item.code for item in PermissionCode.catalog()}
    assert PermissionCode.AUDIT_READ in codes
    assert PermissionCode.SCIM_PROVISION in codes
    assert codes <= catalog
    assert PermissionCode.AUDIT_READ in PermissionCode.admin_role_codes()
