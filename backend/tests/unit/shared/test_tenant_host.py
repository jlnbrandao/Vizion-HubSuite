"""Unit tests for tenant Host / subdomain parsing."""

from __future__ import annotations

import pytest

from src.shared.infrastructure.exceptions import ValidationError
from src.shared.infrastructure.tenant_host import extract_tenant_slug_from_host


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("bigbang.lanstar.com.br", "bigbang"),
        ("bigbang.lanstar.com.br:443", "bigbang"),
        ("bigbang.134.23.23.56", "bigbang"),
        ("bigbang.localhost", "bigbang"),
        ("bigbang.localhost:9000", "bigbang"),
    ],
)
def test_extract_tenant_slug_ok(host: str, expected: str) -> None:
    assert extract_tenant_slug_from_host(host) == expected


@pytest.mark.parametrize(
    "host",
    [
        None,
        "",
        "localhost",
        "localhost:9000",
        "127.0.0.1",
        "192.168.0.1",
        "www.lanstar.com.br",
        "api.lanstar.com.br",
        "bigbang",
    ],
)
def test_extract_tenant_slug_rejects(host: str | None) -> None:
    with pytest.raises(ValidationError):
        extract_tenant_slug_from_host(host)
