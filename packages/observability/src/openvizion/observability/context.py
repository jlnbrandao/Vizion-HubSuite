"""Request-scoped correlation fields. Never log secrets or unnecessary PII."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
TENANT_ID_HEADER = "X-Tenant-ID"
USER_ID_HEADER = "X-User-ID"
SERVICE_HEADER = "X-Service"

_context: ContextVar["ObservabilityContext | None"] = ContextVar(
    "observability_context", default=None
)


@dataclass(frozen=True, slots=True)
class ObservabilityContext:
    request_id: str
    correlation_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    service: str | None = None

    def as_log_fields(self) -> dict[str, str]:
        fields = {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
        }
        if self.tenant_id:
            fields["tenant_id"] = self.tenant_id
        if self.user_id:
            fields["user_id"] = self.user_id
        if self.service:
            fields["service"] = self.service
        return fields


def bind_context(
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    service: str | None = None,
) -> tuple[Token["ObservabilityContext | None"], ObservabilityContext]:
    rid = (request_id or "").strip()[:64] or uuid4().hex
    cid = (correlation_id or "").strip()[:64] or rid
    ctx = ObservabilityContext(
        request_id=rid,
        correlation_id=cid,
        tenant_id=tenant_id,
        user_id=user_id,
        service=service,
    )
    return _context.set(ctx), ctx


def reset_context(token: Token["ObservabilityContext | None"]) -> None:
    _context.reset(token)


def get_context() -> ObservabilityContext | None:
    return _context.get()
