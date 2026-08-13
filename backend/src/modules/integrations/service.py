"""Integration Hub application service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.config.settings import Settings
from src.modules.integrations.layer import IntegrationLayer
from src.modules.integrations.models import (
    IntegrationLogModel,
    IntegrationModel,
    IntegrationWebhookDeliveryModel,
)
from src.modules.integrations.providers.webhook_provider import (
    SUPPORTED_EVENTS,
    verify_hmac_signature,
)
from src.modules.integrations.schemas import (
    CreateIntegrationRequest,
    IntegrationLogResponse,
    IntegrationResponse,
    IntegrationStatusResponse,
    IntegrationSyncResponse,
    IntegrationTestResponse,
    UpdateIntegrationRequest,
    WebhookReceiveResponse,
)
from src.modules.integrations.secrets import decrypt_secrets, encrypt_secrets
from src.shared.infrastructure.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id

_ALLOWED_TYPES = frozenset(
    {
        "rest",
        "oauth2",
        "mtls",
        "webhook",
        "sftp",
        "http_file",
        "soap",
        "incremental_sync",
        "database",
    }
)


class IntegrationService:
    def __init__(self, settings: Settings, layer: IntegrationLayer | None = None) -> None:
        self._settings = settings
        self._layer = layer or IntegrationLayer()

    async def list(self) -> list[IntegrationResponse]:
        session = get_current_session()
        tenant_id = require_current_tenant_id()
        result = await session.execute(
            select(IntegrationModel)
            .where(IntegrationModel.tenant_id == tenant_id)
            .order_by(IntegrationModel.created_at.desc())
        )
        return [self._to_response(row) for row in result.scalars().all()]

    async def get(self, integration_id: UUID) -> IntegrationResponse:
        return self._to_response(await self._require(integration_id))

    async def create(self, body: CreateIntegrationRequest) -> IntegrationResponse:
        if body.type not in _ALLOWED_TYPES:
            raise ValidationError(f"Tipo de integração inválido: {body.type}")

        session = get_current_session()
        tenant_id = require_current_tenant_id()
        await self._ensure_unique_name(tenant_id, body.name.strip())

        configuration = _normalize_configuration(body.type, body.configuration)
        encrypted = encrypt_secrets(self._settings, body.secrets)
        now = datetime.now(UTC)
        row = IntegrationModel(
            id=uuid4(),
            tenant_id=tenant_id,
            name=body.name.strip(),
            description=(body.description or "").strip(),
            type=body.type,
            status=body.status,
            configuration=configuration,
            secrets_encrypted=encrypted,
            secrets_configured=bool(encrypted),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        await self._append_log(row, "info", f"Integration created: {row.name}")
        await session.flush()
        return self._to_response(row)

    async def update(
        self, integration_id: UUID, body: UpdateIntegrationRequest
    ) -> IntegrationResponse:
        session = get_current_session()
        row = await self._require(integration_id)
        if body.name is not None and body.name.strip() != row.name:
            await self._ensure_unique_name(
                row.tenant_id, body.name.strip(), exclude_id=row.id
            )
            row.name = body.name.strip()
        if body.description is not None:
            row.description = body.description.strip()
        if body.status is not None:
            row.status = body.status
        if body.configuration is not None:
            row.configuration = _normalize_configuration(row.type, body.configuration)
        if body.secrets is not None:
            if body.secrets == {}:
                row.secrets_encrypted = None
                row.secrets_configured = False
            else:
                existing = decrypt_secrets(self._settings, row.secrets_encrypted)
                merged = {**existing, **body.secrets}
                encrypted = encrypt_secrets(self._settings, merged)
                if encrypted:
                    row.secrets_encrypted = encrypted
                    row.secrets_configured = True
                elif not existing:
                    row.secrets_encrypted = None
                    row.secrets_configured = False
        row.updated_at = datetime.now(UTC)
        await self._append_log(row, "info", f"Integration updated: {row.name}")
        await session.flush()
        return self._to_response(row)

    async def delete(self, integration_id: UUID) -> None:
        session = get_current_session()
        row = await self._require(integration_id)
        await session.delete(row)
        await session.flush()

    async def get_status(self, integration_id: UUID) -> IntegrationStatusResponse:
        row = await self._require(integration_id)
        return IntegrationStatusResponse(
            id=row.id,
            status=row.status,
            last_sync_at=row.last_sync_at,
            last_error=row.last_error,
        )

    async def list_logs(
        self, integration_id: UUID, *, limit: int = 50
    ) -> list[IntegrationLogResponse]:
        await self._require(integration_id)
        session = get_current_session()
        tenant_id = require_current_tenant_id()
        result = await session.execute(
            select(IntegrationLogModel)
            .where(
                IntegrationLogModel.tenant_id == tenant_id,
                IntegrationLogModel.integration_id == integration_id,
            )
            .order_by(IntegrationLogModel.created_at.desc())
            .limit(min(max(limit, 1), 200))
        )
        return [
            IntegrationLogResponse(
                id=log.id,
                integration_id=log.integration_id,
                level=log.level,
                message=log.message,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]

    async def test(self, integration_id: UUID) -> IntegrationTestResponse:
        session = get_current_session()
        row = await self._require(integration_id)
        row.status = "TESTING"
        row.updated_at = datetime.now(UTC)
        await session.flush()

        secrets = decrypt_secrets(self._settings, row.secrets_encrypted)
        try:
            result = await self._layer.test_connection(
                integration_type=row.type,
                configuration=dict(row.configuration or {}),
                secrets=secrets,
            )
        except ValidationError as exc:
            row.status = "ERROR"
            row.last_error = exc.message
            row.updated_at = datetime.now(UTC)
            await self._append_log(row, "error", exc.message)
            await session.flush()
            return IntegrationTestResponse(
                success=False,
                message="Falha na conexão",
                error_detail=exc.message,
            )

        if result.success:
            row.status = "ACTIVE"
            row.last_error = None
            await self._append_log(
                row,
                "info",
                f"Connection test OK ({result.duration_ms or '—'} ms)",
            )
        else:
            row.status = "ERROR"
            row.last_error = result.error_detail or result.message
            await self._append_log(row, "error", row.last_error)
        row.updated_at = datetime.now(UTC)
        await session.flush()
        return IntegrationTestResponse(
            success=result.success,
            message=result.message,
            server=result.server,
            duration_ms=result.duration_ms,
            authentication=result.authentication,
            permission=result.permission,
            error_detail=result.error_detail,
        )

    async def sync(self, integration_id: UUID) -> IntegrationSyncResponse:
        session = get_current_session()
        row = await self._require(integration_id)
        row.status = "SYNCING"
        row.updated_at = datetime.now(UTC)
        await session.flush()

        secrets = decrypt_secrets(self._settings, row.secrets_encrypted)
        try:
            result = await self._layer.sync(
                integration_type=row.type,
                configuration=dict(row.configuration or {}),
                secrets=secrets,
            )
        except ValidationError as exc:
            row.status = "ERROR"
            row.last_error = exc.message
            row.updated_at = datetime.now(UTC)
            await self._append_log(row, "error", exc.message)
            await session.flush()
            return IntegrationSyncResponse(
                success=False,
                mode="full",
                records_processed=0,
                message=exc.message,
                started_at=datetime.now(UTC).isoformat(),
                finished_at=datetime.now(UTC).isoformat(),
                cursor_value=None,
            )

        if result.success:
            row.status = "ACTIVE"
            row.last_error = None
            row.last_sync_at = datetime.now(UTC)
            if result.cursor_value is not None:
                _persist_cursor(row, result.cursor_value)
            await self._append_log(row, "info", result.message)
        else:
            row.status = "ERROR"
            row.last_error = result.message
            # Persist partial cursor progress on failure when the provider advanced it.
            if result.cursor_value is not None:
                _persist_cursor(row, result.cursor_value)
            await self._append_log(row, "error", result.message)
        row.updated_at = datetime.now(UTC)
        await session.flush()
        return IntegrationSyncResponse(
            success=result.success,
            mode=result.mode,
            records_processed=result.records_processed,
            message=result.message,
            started_at=result.started_at,
            finished_at=result.finished_at,
            cursor_value=result.cursor_value,
        )

    async def receive_webhook(
        self,
        integration_id: UUID,
        *,
        raw_body: bytes,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> WebhookReceiveResponse:
        """Inbound webhook: HMAC auth, event validation, idempotency, logs."""
        session = get_current_session()
        row = await self._require(integration_id)
        if row.type != "webhook":
            raise ValidationError("Integration is not a webhook")
        if row.status == "INACTIVE":
            raise ForbiddenError("Webhook integration is inactive")

        configuration = dict(row.configuration or {})
        secrets = decrypt_secrets(self._settings, row.secrets_encrypted)
        secret = (
            secrets.get("webhook_secret")
            or secrets.get("hmac_secret")
            or secrets.get("signing_secret")
            or secrets.get("secret")
            or ""
        )
        secret = str(secret).strip()
        if not secret:
            await self._append_log(row, "error", "Webhook rejected: signing secret missing")
            raise UnauthorizedError("Webhook signing secret not configured")

        header_name = str(
            configuration.get("signature_header") or "X-Signature"
        ).strip() or "X-Signature"
        header_key = header_name.lower()
        signature_header_value = (
            headers.get(header_key)
            or headers.get("x-signature")
            or headers.get("x-hub-signature-256")
            or headers.get("x-webhook-signature")
            or ""
        )
        if not verify_hmac_signature(
            secret=secret,
            body=raw_body,
            signature_header=signature_header_value,
        ):
            await self._append_log(
                row, "error", f"Webhook rejected: invalid signature ({header_name})"
            )
            raise UnauthorizedError("Invalid webhook signature")

        event_type = str(
            payload.get("event_type") or payload.get("type") or payload.get("event") or ""
        ).strip()
        allowed = {
            str(item).strip()
            for item in (configuration.get("event_types") or [])
            if str(item).strip()
        } or set(SUPPORTED_EVENTS)
        if event_type not in SUPPORTED_EVENTS:
            await self._append_log(
                row, "error", f"Webhook rejected: unsupported event '{event_type}'"
            )
            raise ValidationError(f"Unsupported event type: {event_type or '—'}")
        if event_type not in allowed:
            await self._append_log(
                row, "error", f"Webhook rejected: event '{event_type}' not enabled"
            )
            raise ValidationError(f"Event type not enabled for this integration: {event_type}")

        key = (
            (headers.get("idempotency-key") or "").strip()
            or str(payload.get("id") or payload.get("event_id") or "").strip()
            or str(payload.get("delivery_id") or "").strip()
        )
        if not key:
            # Deterministic fallback — same payload retries collide.
            import hashlib

            key = hashlib.sha256(raw_body).hexdigest()[:64]

        existing = (
            await session.execute(
                select(IntegrationWebhookDeliveryModel).where(
                    IntegrationWebhookDeliveryModel.integration_id == row.id,
                    IntegrationWebhookDeliveryModel.idempotency_key == key,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.attempt_count += 1
            existing.updated_at = datetime.now(UTC)
            if existing.status == "processed":
                await self._append_log(
                    row,
                    "info",
                    f"Webhook duplicate ignored: {event_type} ({key[:16]}…)",
                )
                await session.flush()
                return WebhookReceiveResponse(
                    accepted=True,
                    duplicate=True,
                    event_type=event_type,
                    delivery_id=existing.id,
                    message="Duplicate delivery ignored (idempotent)",
                )
            # Previous attempt failed — retry processing.
            try:
                _process_webhook_event(event_type, payload)
                existing.status = "processed"
                existing.last_error = None
                row.status = "ACTIVE"
                row.last_error = None
                row.last_sync_at = datetime.now(UTC)
                await self._append_log(
                    row,
                    "info",
                    f"Webhook retry processed: {event_type} (attempt {existing.attempt_count})",
                )
            except Exception as exc:  # noqa: BLE001 — convert to failed delivery
                existing.status = "failed"
                existing.last_error = str(exc)[:500]
                row.status = "ERROR"
                row.last_error = existing.last_error
                await self._append_log(row, "error", f"Webhook retry failed: {existing.last_error}")
                await session.flush()
                raise ValidationError("Webhook processing failed; retry later") from exc
            row.updated_at = datetime.now(UTC)
            await session.flush()
            return WebhookReceiveResponse(
                accepted=True,
                duplicate=False,
                event_type=event_type,
                delivery_id=existing.id,
                message="Webhook processed after retry",
            )

        delivery = IntegrationWebhookDeliveryModel(
            id=uuid4(),
            tenant_id=row.tenant_id,
            integration_id=row.id,
            idempotency_key=key,
            event_type=event_type,
            payload=payload,
            status="received",
            attempt_count=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(delivery)
        await session.flush()

        try:
            _process_webhook_event(event_type, payload)
            delivery.status = "processed"
            delivery.last_error = None
            row.status = "ACTIVE"
            row.last_error = None
            row.last_sync_at = datetime.now(UTC)
            await self._append_log(row, "info", f"Webhook received: {event_type}")
        except Exception as exc:  # noqa: BLE001
            delivery.status = "failed"
            delivery.last_error = str(exc)[:500]
            row.status = "ERROR"
            row.last_error = delivery.last_error
            await self._append_log(row, "error", f"Webhook failed: {delivery.last_error}")
            await session.flush()
            raise ValidationError("Webhook processing failed; retry later") from exc

        row.updated_at = datetime.now(UTC)
        await session.flush()
        return WebhookReceiveResponse(
            accepted=True,
            duplicate=False,
            event_type=event_type,
            delivery_id=delivery.id,
            message="Webhook accepted",
        )

    async def _require(self, integration_id: UUID) -> IntegrationModel:
        session = get_current_session()
        tenant_id = require_current_tenant_id()
        result = await session.execute(
            select(IntegrationModel).where(
                IntegrationModel.id == integration_id,
                IntegrationModel.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError("Integration not found")
        return row

    async def _ensure_unique_name(
        self,
        tenant_id: UUID,
        name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        session = get_current_session()
        stmt = select(IntegrationModel.id).where(
            IntegrationModel.tenant_id == tenant_id,
            IntegrationModel.name == name,
        )
        if exclude_id is not None:
            stmt = stmt.where(IntegrationModel.id != exclude_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise ConflictError(f"Integration name already exists: {name}")

    async def _append_log(self, row: IntegrationModel, level: str, message: str) -> None:
        session = get_current_session()
        session.add(
            IntegrationLogModel(
                id=uuid4(),
                tenant_id=row.tenant_id,
                integration_id=row.id,
                level=level,
                message=message,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _to_response(row: IntegrationModel) -> IntegrationResponse:
        return IntegrationResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            type=row.type,
            status=row.status,
            configuration=dict(row.configuration or {}),
            secrets_configured=bool(row.secrets_configured),
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_sync_at=row.last_sync_at,
            last_error=row.last_error,
        )


def _persist_cursor(row: IntegrationModel, cursor_value: str) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    cfg = dict(row.configuration or {})
    cfg["cursor_value"] = cursor_value
    row.configuration = cfg
    flag_modified(row, "configuration")


def _normalize_configuration(
    integration_type: str, configuration: dict[str, Any]
) -> dict[str, Any]:
    """Accept camelCase from the Vue form and persist snake_case keys."""
    aliases = {
        "baseUrl": "base_url",
        "httpMethod": "http_method",
        "authType": "auth_type",
        "timeoutMs": "timeout_ms",
        "rateLimitPerMinute": "rate_limit_per_minute",
        "apiKeyHeader": "api_key_header",
        "tokenUrl": "token_url",
        "clientId": "client_id",
        "grantType": "grant_type",
        "eventTypes": "event_types",
        "signatureHeader": "signature_header",
        "remotePath": "remote_path",
        "filenamePattern": "filename_pattern",
        "scheduleCron": "schedule_cron",
        "wsdlUrl": "wsdl_url",
        "soapAction": "soap_action",
        "cursorField": "cursor_field",
        "cursorValue": "cursor_value",
        "pageSize": "page_size",
        "readOnly": "read_only",
        "rowLimit": "row_limit",
        "secretsConfigured": "secrets_configured",
    }
    normalized: dict[str, Any] = {}
    for key, value in (configuration or {}).items():
        if key == "secretsConfigured":
            continue  # persisted as column, not configuration
        target = aliases.get(key, key)
        normalized[target] = value

    if integration_type == "rest":
        normalized.setdefault("endpoint", "/")
        normalized.setdefault("http_method", "GET")
        normalized.setdefault("auth_type", "none")
        normalized.setdefault("timeout_ms", 30_000)
        normalized.setdefault("pagination", "none")
    elif integration_type == "oauth2":
        normalized.setdefault("grant_type", "client_credentials")
        normalized.setdefault("timeout_ms", 30_000)
        normalized.setdefault("pagination", "none")
    elif integration_type == "mtls":
        normalized.setdefault("endpoint", "/")
        normalized.setdefault("timeout_ms", 30_000)
        normalized.setdefault("pagination", "none")
    elif integration_type == "webhook":
        normalized.setdefault(
            "event_types",
            ["address.created", "address.updated", "address.deleted"],
        )
        normalized.setdefault("signature_header", "X-Signature")
    elif integration_type == "sftp":
        normalized.setdefault("port", 22)
        normalized.setdefault("auth_type", "private_key")
        normalized.setdefault("remote_path", "/")
        normalized.setdefault("filename_pattern", "*.csv")
        normalized.setdefault("encoding", "utf-8")
        normalized.setdefault("delimiter", ",")
        normalized.setdefault("schedule_cron", "0 */6 * * *")
    elif integration_type == "http_file":
        normalized.setdefault("format", "json")
        normalized.setdefault("auth_type", "none")
        normalized.setdefault("encoding", "utf-8")
        normalized.setdefault("delimiter", ",")
        normalized.setdefault("timeout_ms", 30_000)
    elif integration_type == "soap":
        normalized.setdefault("auth_type", "none")
        normalized.setdefault("timeout_ms", 30_000)
        normalized.setdefault("namespace", "urn:integration")
    elif integration_type == "incremental_sync":
        normalized.setdefault("endpoint", "/")
        normalized.setdefault("cursor_field", "updated_since")
        normalized.setdefault("page_size", 100)
        normalized.setdefault("auth_type", "none")
        normalized.setdefault("timeout_ms", 30_000)
    elif integration_type == "database":
        # Always force read-only — never allow write mode from the client.
        normalized["read_only"] = True
        normalized.setdefault("port", 5432)
        normalized.setdefault("schema", "public")
        normalized.setdefault("row_limit", 1000)
        normalized.setdefault("timeout_ms", 15_000)
    return normalized


def _process_webhook_event(event_type: str, payload: dict[str, Any]) -> None:
    """Domain hook for address.* events — validate shape; extend with handlers later."""
    if event_type not in SUPPORTED_EVENTS:
        raise ValidationError(f"Unsupported event type: {event_type}")
    # Minimal validation: address events should carry an address identifier when present.
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    address_id = data.get("address_id") or data.get("id")
    if address_id is None:
        # Allow heartbeat-style payloads that only announce the event type.
        return
    if not str(address_id).strip():
        raise ValidationError("address id is empty")
