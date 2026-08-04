"""Handler contracts for Commands and Queries.

Handlers orchestrate: load aggregates, call domain methods, persist via UoW.
They must NOT contain complex business rules — those belong to the Domain.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.shared.application.command import Command
from src.shared.application.query import Query

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)
TResult = TypeVar("TResult")


class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Execute a write use case and return a result (often an ID or DTO)."""


class QueryHandler(ABC, Generic[TQuery, TResult]):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Execute a read use case and return a result DTO / projection."""
