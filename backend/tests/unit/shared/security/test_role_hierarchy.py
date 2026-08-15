"""Unit tests for role privilege hierarchy (rank table + engine policy)."""

from __future__ import annotations

from src.shared.infrastructure.security.authorization import HierarchyPolicy
from src.shared.infrastructure.security.role_hierarchy import role_rank


def test_role_rank_ordering() -> None:
    assert role_rank(["ADMIN"]) > role_rank(["MANAGER"])
    assert role_rank(["MANAGER"]) > role_rank(["OPERATOR"])
    assert role_rank(["ADMIN", "VIEWER"]) == role_rank(["ADMIN"])
    assert role_rank([]) == 0
    assert role_rank(["CUSTOM"]) == 0


def test_can_manage_strictly_outranks() -> None:
    assert HierarchyPolicy.can_manage(["ADMIN"], ["MANAGER"])
    assert HierarchyPolicy.can_manage(["MANAGER"], ["OPERATOR"])
    assert not HierarchyPolicy.can_manage(["MANAGER"], ["ADMIN"])
    assert not HierarchyPolicy.can_manage(["ADMIN"], ["ADMIN"])
    assert not HierarchyPolicy.can_manage(["MANAGER"], ["MANAGER"])


def test_can_grant_requires_strictly_higher() -> None:
    assert HierarchyPolicy.can_grant(["ADMIN"], ["MANAGER", "OPERATOR"])
    assert HierarchyPolicy.can_grant(["PLATFORM"], ["ADMIN", "MANAGER"])
    assert not HierarchyPolicy.can_grant(["ADMIN"], ["ADMIN"])
    assert not HierarchyPolicy.can_grant(["MANAGER"], ["ADMIN"])
    assert not HierarchyPolicy.can_grant(["MANAGER"], ["MANAGER"])
    assert HierarchyPolicy.can_grant(["MANAGER"], ["OPERATOR", "VIEWER"])
