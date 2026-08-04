"""Aggregate Root — consistency boundary that collects Domain Events.

Only Aggregate Roots publish events. Child entities mutate through the root.
Handlers never publish events directly; they call domain methods that raise them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.domain.domain_event import DomainEvent
from src.shared.domain.entity import Entity


@dataclass(eq=False, kw_only=True)
class AggregateRoot(Entity):
    _domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def raise_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_domain_events(self) -> list[DomainEvent]:
        """Return and clear pending events (called by Unit of Work after persist)."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    @property
    def domain_events(self) -> list[DomainEvent]:
        return list(self._domain_events)
