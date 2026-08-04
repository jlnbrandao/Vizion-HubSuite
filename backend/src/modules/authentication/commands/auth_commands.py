"""Authentication write commands."""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.application.command import Command


@dataclass(frozen=True, kw_only=True)
class LoginCommand(Command):
    email: str
    password: str


@dataclass(frozen=True, kw_only=True)
class LogoutCommand(Command):
    refresh_token: str


@dataclass(frozen=True, kw_only=True)
class RefreshTokenCommand(Command):
    refresh_token: str
