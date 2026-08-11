"""Role privilege ranks for hierarchical authorization checks.

Higher rank may manage lower rank. Peers and superiors cannot be managed.
Unknown / custom role names default to rank 0.
"""

from __future__ import annotations

from collections.abc import Iterable

ROLE_RANK: dict[str, int] = {
    "ADMIN": 100,
    "MANAGER": 80,
    "OPERATOR": 60,
    "CLIENT": 40,
    "VIEWER": 20,
}


def role_rank(role_names: Iterable[str]) -> int:
    return max((ROLE_RANK.get(name.upper(), 0) for name in role_names), default=0)


def can_manage(actor_roles: Iterable[str], target_roles: Iterable[str]) -> bool:
    """True when the actor outranks the target (strictly greater)."""
    return role_rank(actor_roles) > role_rank(target_roles)


def can_grant_roles(actor_roles: Iterable[str], granted_roles: Iterable[str]) -> bool:
    """True when the actor may grant every listed role (rank >= each role)."""
    actor = role_rank(actor_roles)
    return all(actor >= ROLE_RANK.get(name.upper(), 0) for name in granted_roles)
