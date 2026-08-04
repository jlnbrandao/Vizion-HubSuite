"""Request-scoped AsyncSession via ContextVar.

Unit of Work binds the session on enter; repositories read it without being
constructed inside handlers — both are injected by the DI container.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

from sqlalchemy.ext.asyncio import AsyncSession

_session_ctx: ContextVar[AsyncSession | None] = ContextVar("db_session", default=None)


def bind_session(session: AsyncSession) -> Token[AsyncSession | None]:
    return _session_ctx.set(session)


def unbind_session(token: Token[AsyncSession | None]) -> None:
    _session_ctx.reset(token)


def get_current_session() -> AsyncSession:
    session = _session_ctx.get()
    if session is None:
        raise RuntimeError(
            "No active database session. Repositories must be used inside a UnitOfWork."
        )
    return session
