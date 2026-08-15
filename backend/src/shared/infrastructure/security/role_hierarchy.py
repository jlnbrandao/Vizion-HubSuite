"""Role privilege ranks — the rank table only.

Higher rank may manage lower rank. Peers and superiors cannot be managed.
Unknown / custom role names default to rank 0.

The comparison rules live in `authorization.HierarchyPolicy`, so the decision has
a single owner; this module stays a pure lookup table to avoid an import cycle.
"""

from __future__ import annotations

from collections.abc import Iterable

ROLE_RANK: dict[str, int] = {
    "PLATFORM": 200,
    "ADMIN": 100,
    "MANAGER": 80,
    "OPERATOR": 60,
    "CLIENT": 40,
    "VIEWER": 20,
}


def role_rank(role_names: Iterable[str]) -> int:
    return max((ROLE_RANK.get(name.upper(), 0) for name in role_names), default=0)
