"""Integration secrets encrypt/decrypt."""

from __future__ import annotations

from src.config.settings import Settings
from src.modules.integrations.secrets import decrypt_secrets, encrypt_secrets


def test_encrypt_decrypt_roundtrip() -> None:
    settings = Settings(jwt_secret_key="unit-test-secret-key-32chars-min!!")
    blob = encrypt_secrets(settings, {"bearer_token": "abc", "empty": ""})
    assert blob is not None
    assert "abc" not in blob
    restored = decrypt_secrets(settings, blob)
    assert restored == {"bearer_token": "abc"}


def test_encrypt_empty_returns_none() -> None:
    settings = Settings(jwt_secret_key="unit-test-secret-key-32chars-min!!")
    assert encrypt_secrets(settings, None) is None
    assert encrypt_secrets(settings, {}) is None
    assert encrypt_secrets(settings, {"x": ""}) is None
