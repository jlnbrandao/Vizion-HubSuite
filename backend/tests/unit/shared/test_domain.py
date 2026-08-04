"""Unit tests for Shared Kernel Domain building blocks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent
from src.shared.domain.entity import Entity
from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class SampleEvent(DomainEvent):
    message: str = "hello"


@dataclass(eq=False, kw_only=True)
class SampleAggregate(AggregateRoot):
    name: str = "test"

    def rename(self, name: str) -> None:
        self.name = name
        self.touch()
        self.raise_event(SampleEvent(aggregate_id=self.id, message=f"renamed to {name}"))


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    def _validate(self) -> None:
        if "@" not in self.value:
            raise ValueError("Invalid email")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Email:
        return cls(value=value)


def test_entity_equality_by_id() -> None:
    shared_id = uuid4()

    @dataclass(eq=False, kw_only=True)
    class A(Entity):
        label: str = "a"

    a1 = A(id=shared_id, label="one")
    a2 = A(id=shared_id, label="two")
    a3 = A(label="three")

    assert a1 == a2
    assert a1 != a3
    assert hash(a1) == hash(a2)


def test_aggregate_collects_and_pulls_events() -> None:
    agg = SampleAggregate(name="before")
    agg.rename("after")

    assert len(agg.domain_events) == 1
    events = agg.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_name == "SampleEvent"
    assert agg.domain_events == []


def test_value_object_validation_and_equality() -> None:
    e1 = Email(value="user@example.com")
    e2 = Email(value="user@example.com")
    e3 = Email(value="other@example.com")

    assert e1 == e2
    assert e1 != e3
    assert e1.to_primitive() == "user@example.com"

    with pytest.raises(ValueError, match="Invalid email"):
        Email(value="not-an-email")
