"""ASGI middleware — bind a correlation id to every request.

An inbound `X-Request-ID` is honoured so a reverse proxy or the SPA can correlate
a call end-to-end; otherwise one is generated. Audit events store it, which is
what turns "a denial happened" into "this request was denied".
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.shared.infrastructure.request_context import (
    REQUEST_ID_HEADER,
    bind_request_id,
    unbind_request_id,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token, request_id = bind_request_id(request.headers.get(REQUEST_ID_HEADER))
        try:
            response = await call_next(request)
        finally:
            unbind_request_id(token)
        response.headers.setdefault(REQUEST_ID_HEADER, request_id)
        return response
