"""Query marker — read-side intent (CQRS).

Queries never mutate state. Handlers may bypass Aggregates and read
optimized projections / SQL views for performance.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Query(ABC):
    """Immutable read intent. Subclass per use case (e.g. GetUserByIdQuery)."""
