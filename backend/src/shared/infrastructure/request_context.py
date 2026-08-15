"""Request correlation id, propagated through logs and audit events."""

from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def bind_request_id(request_id: str | None = None) -> tuple[Token[str | None], str]:
    value = (request_id or "").strip()[:64] or uuid4().hex
    return _request_id.set(value), value


def unbind_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()
