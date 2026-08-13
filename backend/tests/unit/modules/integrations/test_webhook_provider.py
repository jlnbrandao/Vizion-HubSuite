"""Unit tests for WebhookProvider and HMAC verification."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from src.modules.integrations.providers.webhook_provider import (
    WebhookProvider,
    verify_hmac_signature,
)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_verify_hmac_raw_hex() -> None:
    body = b'{"event_type":"address.created"}'
    secret = "whsec_test"
    assert verify_hmac_signature(
        secret=secret,
        body=body,
        signature_header=_sign(secret, body),
    )


def test_verify_hmac_sha256_prefix() -> None:
    body = b'{"event_type":"address.updated"}'
    secret = "whsec_test"
    digest = _sign(secret, body)
    assert verify_hmac_signature(
        secret=secret,
        body=body,
        signature_header=f"sha256={digest}",
    )


def test_verify_hmac_rejects_bad_signature() -> None:
    body = b'{"event_type":"address.deleted"}'
    assert not verify_hmac_signature(
        secret="whsec_test",
        body=body,
        signature_header="deadbeef",
    )


@pytest.mark.asyncio
async def test_webhook_test_connection_ready() -> None:
    provider = WebhookProvider()
    result = await provider.test_connection(
        configuration={
            "event_types": ["address.created", "address.updated"],
            "signature_header": "X-Signature",
        },
        secrets={"webhook_secret": "whsec_abc"},
    )
    assert result.success is True
    assert result.authentication == "HMAC-SHA256 (X-Signature)"
    assert "address.created" in (result.permission or "")


@pytest.mark.asyncio
async def test_webhook_test_connection_missing_secret() -> None:
    provider = WebhookProvider()
    result = await provider.test_connection(
        configuration={"event_types": ["address.created"]},
        secrets={},
    )
    assert result.success is False
    assert "segredo" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_webhook_test_connection_unknown_event() -> None:
    provider = WebhookProvider()
    result = await provider.test_connection(
        configuration={"event_types": ["address.created", "foo.bar"]},
        secrets={"webhook_secret": "x"},
    )
    assert result.success is False
    assert "foo.bar" in (result.error_detail or "")


@pytest.mark.asyncio
async def test_webhook_sync_is_push_based() -> None:
    provider = WebhookProvider()
    result = await provider.sync(
        configuration={"event_types": ["address.deleted"]},
        secrets={"webhook_secret": "x"},
    )
    assert result.success is True
    assert "push" in result.message.lower()
