"""Permission catalog includes IAM codes."""

from __future__ import annotations

from src.shared.infrastructure.security.permission_codes import PermissionCode


def test_iam_permission_codes_in_catalog() -> None:
    codes = set(PermissionCode.all_codes())
    assert PermissionCode.AUDIT_READ in codes
    assert PermissionCode.SCIM_PROVISION in codes
    # Constants are the legacy form; the catalog answers to both.
    assert codes <= PermissionCode.known_codes()
    assert PermissionCode.AUDIT_READ in PermissionCode.admin_role_codes()


def test_iam_codes_are_namespaced_under_iam() -> None:
    assert PermissionCode.canonical(PermissionCode.AUDIT_READ) == "iam.audit.read"
    assert PermissionCode.canonical(PermissionCode.TENANTS_READ) == "platform.tenants.read"
    assert PermissionCode.service_of(PermissionCode.SCIM_PROVISION) == "iam"
