"""Unit tests for AuthZ require_* helpers (without FastAPI wiring)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


def _user(*permissions: str, roles: tuple[str, ...] = ()) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="u@x.com",
        full_name="User",
        tenant_id=uuid4(),
        tenant_slug="bigbang",
        tenant_name="Bigbang",
        role_names=frozenset(r.upper() for r in roles),
        permissions=frozenset(permissions),
    )


def test_permission_gate_logic() -> None:
    admin = _user(
        PermissionCode.USERS_CREATE,
        PermissionCode.USERS_READ,
        roles=("ADMIN",),
    )
    viewer = _user(PermissionCode.USERS_READ, roles=("VIEWER",))

    assert admin.has_all_permissions(PermissionCode.USERS_CREATE)
    assert not viewer.has_permission(PermissionCode.USERS_CREATE)

    if not viewer.has_permission(PermissionCode.USERS_CREATE):
        with pytest.raises(ForbiddenError):
            raise ForbiddenError(f"Missing permission(s): {PermissionCode.USERS_CREATE}")
