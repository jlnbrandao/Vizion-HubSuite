"""In-process Command Bus.

Routes a Command to its registered CommandHandler.
Handlers are registered at composition root (DI), never discovered by reflection in production
so wiring stays explicit and fail-fast.
"""

from __future__ import annotations

from typing import Any, TypeVar

from src.shared.application.command import Command
from src.shared.application.handler import CommandHandler

TResult = TypeVar("TResult")


class CommandHandlerNotFoundError(LookupError):
    def __init__(self, command_type: type[Command]) -> None:
        super().__init__(f"No handler registered for command: {command_type.__name__}")
        self.command_type = command_type


class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Command], CommandHandler[Any, Any]] = {}

    def register(
        self,
        command_type: type[Command],
        handler: CommandHandler[Any, Any],
    ) -> None:
        if command_type in self._handlers:
            raise ValueError(f"Handler already registered for {command_type.__name__}")
        self._handlers[command_type] = handler

    async def execute(self, command: Command) -> Any:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise CommandHandlerNotFoundError(type(command))
        return await handler.handle(command)

    def is_registered(self, command_type: type[Command]) -> bool:
        return command_type in self._handlers

    @property
    def registered_commands(self) -> list[type[Command]]:
        return list(self._handlers.keys())
