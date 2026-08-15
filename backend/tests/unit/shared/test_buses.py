"""Unit tests for Command Bus, Query Bus and Event Bus."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.shared.application.command import Command
from src.shared.application.command_bus import CommandBus, CommandHandlerNotFoundError
from src.shared.application.event_bus import EventBus
from src.shared.application.handler import CommandHandler, QueryHandler
from src.shared.application.query import Query
from src.shared.application.query_bus import QueryBus, QueryHandlerNotFoundError
from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class GreetCommand(Command):
    name: str


@dataclass(frozen=True, kw_only=True)
class GetGreetingQuery(Query):
    name: str


@dataclass(frozen=True, kw_only=True)
class GreetedEvent(DomainEvent):
    name: str = ""


class GreetHandler(CommandHandler[GreetCommand, str]):
    async def handle(self, command: GreetCommand) -> str:
        return f"Hello, {command.name}"


class GetGreetingHandler(QueryHandler[GetGreetingQuery, str]):
    async def handle(self, query: GetGreetingQuery) -> str:
        return f"Greeting for {query.name}"


@pytest.mark.asyncio
async def test_command_bus_dispatches_to_handler() -> None:
    bus = CommandBus()
    bus.register(GreetCommand, GreetHandler())

    result = await bus.execute(GreetCommand(name="Vizion"))
    assert result == "Hello, Vizion"
    assert bus.is_registered(GreetCommand)


@pytest.mark.asyncio
async def test_command_bus_raises_when_handler_missing() -> None:
    bus = CommandBus()
    with pytest.raises(CommandHandlerNotFoundError):
        await bus.execute(GreetCommand(name="x"))


@pytest.mark.asyncio
async def test_command_bus_rejects_duplicate_registration() -> None:
    bus = CommandBus()
    bus.register(GreetCommand, GreetHandler())
    with pytest.raises(ValueError, match="already registered"):
        bus.register(GreetCommand, GreetHandler())


@pytest.mark.asyncio
async def test_query_bus_dispatches_to_handler() -> None:
    bus = QueryBus()
    bus.register(GetGreetingQuery, GetGreetingHandler())

    result = await bus.ask(GetGreetingQuery(name="Admin"))
    assert result == "Greeting for Admin"


@pytest.mark.asyncio
async def test_query_bus_raises_when_handler_missing() -> None:
    bus = QueryBus()
    with pytest.raises(QueryHandlerNotFoundError):
        await bus.ask(GetGreetingQuery(name="x"))


@pytest.mark.asyncio
async def test_event_bus_fan_out() -> None:
    bus = EventBus()
    received: list[str] = []

    async def audit(event: DomainEvent) -> None:
        assert isinstance(event, GreetedEvent)
        received.append(f"audit:{event.name}")

    async def notify(event: DomainEvent) -> None:
        assert isinstance(event, GreetedEvent)
        received.append(f"notify:{event.name}")

    bus.subscribe(GreetedEvent, audit)
    bus.subscribe(GreetedEvent, notify)

    await bus.publish(GreetedEvent(name="Alice"))

    assert received == ["audit:Alice", "notify:Alice"]
    assert bus.subscriber_count(GreetedEvent) == 2
