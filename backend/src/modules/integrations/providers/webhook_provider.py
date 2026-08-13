"""Webhook provider — inbound push config validation + readiness test."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)

SUPPORTED_EVENTS = frozenset(
    {
        "address.created",
        "address.updated",
        "address.deleted",
    }
)


class WebhookProvider:
    """ETAPA 5: webhook integrations are push-based; provider validates readiness."""

    type = "webhook"

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        events = _event_types(configuration)
        if not events:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Nenhum evento configurado.",
            )
        unknown = sorted(events - SUPPORTED_EVENTS)
        if unknown:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=f"Eventos não suportados: {', '.join(unknown)}",
            )

        secret = _webhook_secret(secrets)
        if not secret:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Segredo de assinatura do webhook não configurado no backend.",
            )

        header = (
            str(
                configuration.get("signature_header")
                or configuration.get("signatureHeader")
                or "X-Signature"
            ).strip()
            or "X-Signature"
        )

        return IntegrationTestResult(
            success=True,
            message="Endpoint de webhook pronto para receber eventos",
            server="inbound-webhook (platform)",
            duration_ms=0,
            authentication=f"HMAC-SHA256 ({header})",
            permission=", ".join(sorted(events)),
            error_detail=None,
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        now = datetime.now(UTC).isoformat()
        events = _event_types(configuration)
        return IntegrationSyncResult(
            success=True,
            mode="incremental",
            records_processed=0,
            message=(
                "Webhooks são push-based; use o endpoint inbound da plataforma. "
                f"Eventos: {', '.join(sorted(events)) or '—'}."
            ),
            started_at=now,
            finished_at=now,
        )


def _event_types(configuration: dict[str, Any]) -> set[str]:
    raw = configuration.get("event_types") or configuration.get("eventTypes") or []
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def _webhook_secret(secrets: dict[str, Any]) -> str:
    for key in ("webhook_secret", "hmac_secret", "signing_secret", "secret"):
        value = secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def verify_hmac_signature(*, secret: str, body: bytes, signature_header: str) -> bool:
    """Validate HMAC-SHA256 signature. Accepts raw hex or sha256=<hex>."""
    import hashlib
    import hmac

    if not secret or not signature_header:
        return False
    provided = signature_header.strip()
    if provided.lower().startswith("sha256="):
        provided = provided.split("=", 1)[1].strip()
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, provided.lower())
