"""Command marker — write-side intent (CQRS).

Commands express *what* the actor wants to change. They carry data only;
validation of shape happens via Pydantic DTOs at the API boundary,
domain invariants live on Aggregates / Value Objects.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Command(ABC):
    """Immutable write intent. Subclass per use case (e.g. CreateUserCommand)."""
