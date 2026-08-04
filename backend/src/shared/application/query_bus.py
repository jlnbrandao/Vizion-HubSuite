"""In-process Query Bus.

Mirrors CommandBus for the read side. Keeping buses separate enforces CQRS:
write handlers never accidentally handle queries and vice versa.
"""

from __future__ import annotations

from typing import Any

from src.shared.application.handler import QueryHandler
from src.shared.application.query import Query


class QueryHandlerNotFoundError(LookupError):
    def __init__(self, query_type: type[Query]) -> None:
        super().__init__(f"No handler registered for query: {query_type.__name__}")
        self.query_type = query_type


class QueryBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Query], QueryHandler[Any, Any]] = {}

    def register(
        self,
        query_type: type[Query],
        handler: QueryHandler[Any, Any],
    ) -> None:
        if query_type in self._handlers:
            raise ValueError(f"Handler already registered for {query_type.__name__}")
        self._handlers[query_type] = handler

    async def ask(self, query: Query) -> Any:
        handler = self._handlers.get(type(query))
        if handler is None:
            raise QueryHandlerNotFoundError(type(query))
        return await handler.handle(query)

    def is_registered(self, query_type: type[Query]) -> bool:
        return query_type in self._handlers

    @property
    def registered_queries(self) -> list[type[Query]]:
        return list(self._handlers.keys())
