"""Shared Kernel — domain building blocks.

Modules import these contracts; they never import each other's internals.
"""

from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent
from src.shared.domain.entity import Entity
from src.shared.domain.repository import Repository
from src.shared.domain.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "Repository",
    "ValueObject",
]
