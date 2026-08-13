"""Encrypt/decrypt integration secrets at rest (Fernet).

Key material comes from settings — never expose decrypted secrets in API responses.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from src.config.settings import Settings


def _fernet(settings: Settings) -> Fernet:
    raw = (settings.integration_secrets_key or settings.jwt_secret_key).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secrets(settings: Settings, secrets: dict[str, Any] | None) -> str | None:
    if not secrets:
        return None
    cleaned = {k: v for k, v in secrets.items() if v is not None and str(v) != ""}
    if not cleaned:
        return None
    payload = json.dumps(cleaned, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet(settings).encrypt(payload).decode("utf-8")


def decrypt_secrets(settings: Settings, blob: str | None) -> dict[str, Any]:
    if not blob:
        return {}
    try:
        raw = _fernet(settings).decrypt(blob.encode("utf-8"))
    except InvalidToken:
        return {}
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else {}
