"""Repository interface (port) — persistence contract for Aggregate Roots.

Implementations live in infrastructure. Domain and application depend only on this ABC.
Repositories must NOT contain business rules — only persistence concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from src.shared.domain.aggregate_root import AggregateRoot

TAggregate = TypeVar("TAggregate", bound=AggregateRoot)


class Repository(ABC, Generic[TAggregate]):
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> TAggregate | None:
        """Load an aggregate by its identity, or None if not found."""

    @abstractmethod
    async def add(self, entity: TAggregate) -> None:
        """Register a new aggregate for insertion within the current Unit of Work."""

    @abstractmethod
    async def update(self, entity: TAggregate) -> None:
        """Mark an existing aggregate as dirty within the current Unit of Work."""

    @abstractmethod
    async def delete(self, entity: TAggregate) -> None:
        """Mark an aggregate for deletion within the current Unit of Work."""

    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check whether an aggregate with the given ID exists."""
