"""Unit tests for CurrentUser permission helpers."""

from __future__ import annotations

from uuid import uuid4

from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


def test_current_user_permission_checks() -> None:
    user = CurrentUser(
        id=uuid4(),
        email="a@b.com",
        full_name="Ada",
        tenant_id=uuid4(),
        tenant_slug="universe",
        tenant_name="Universe",
        role_names=frozenset({"ADMIN"}),
        permissions=frozenset(
            {PermissionCode.USERS_READ, PermissionCode.USERS_CREATE}
        ),
    )

    assert user.has_permission(PermissionCode.USERS_READ)
    assert user.has_all_permissions(
        PermissionCode.USERS_READ, PermissionCode.USERS_CREATE
    )
    assert not user.has_permission(PermissionCode.USERS_DELETE)
    assert user.has_any_permission(PermissionCode.USERS_DELETE, PermissionCode.USERS_READ)
    assert user.has_role("admin")
    assert user.has_any_role("MANAGER", "ADMIN")
    assert not user.has_any_role("VIEWER")
