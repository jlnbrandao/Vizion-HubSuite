"""Shared IAM helpers."""

from __future__ import annotations

import hashlib
import secrets


def sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_api_key_raw() -> tuple[str, str, str]:
    """Returns (prefix, raw_key, key_hash)."""
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    raw = f"lsk_{prefix}_{secret}"
    return prefix, raw, sha256_hex(raw)
