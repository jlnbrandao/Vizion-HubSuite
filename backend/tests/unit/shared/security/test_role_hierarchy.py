"""Unit tests for role privilege hierarchy."""

from __future__ import annotations

from src.shared.infrastructure.security.role_hierarchy import (
    can_grant_roles,
    can_manage,
    role_rank,
)


def test_role_rank_ordering() -> None:
    assert role_rank(["ADMIN"]) > role_rank(["MANAGER"])
    assert role_rank(["MANAGER"]) > role_rank(["OPERATOR"])
    assert role_rank(["ADMIN", "VIEWER"]) == role_rank(["ADMIN"])
    assert role_rank([]) == 0
    assert role_rank(["CUSTOM"]) == 0


def test_can_manage_strictly_outranks() -> None:
    assert can_manage(["ADMIN"], ["MANAGER"])
    assert can_manage(["MANAGER"], ["OPERATOR"])
    assert not can_manage(["MANAGER"], ["ADMIN"])
    assert not can_manage(["ADMIN"], ["ADMIN"])
    assert not can_manage(["MANAGER"], ["MANAGER"])


def test_can_grant_roles_requires_strictly_higher() -> None:
    assert can_grant_roles(["ADMIN"], ["MANAGER", "OPERATOR"])
    assert can_grant_roles(["PLATFORM"], ["ADMIN", "MANAGER"])
    assert not can_grant_roles(["ADMIN"], ["ADMIN"])
    assert not can_grant_roles(["MANAGER"], ["ADMIN"])
    assert not can_grant_roles(["MANAGER"], ["MANAGER"])
    assert can_grant_roles(["MANAGER"], ["OPERATOR", "VIEWER"])
