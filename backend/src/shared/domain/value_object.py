"""Value Object base — immutable, equality by value.

Value Objects have no identity. Two VOs with the same attributes are equal.
Validation belongs in __post_init__ so invalid states cannot be constructed.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, Self


@dataclass(frozen=True)
class ValueObject(ABC):
    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Override to enforce invariants. Raise ValueError on violation."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def to_primitive(self) -> Any:
        """Serialize to a primitive suitable for persistence / API."""
        raise NotImplementedError

    @classmethod
    def from_primitive(cls, value: Any) -> Self:
        raise NotImplementedError
