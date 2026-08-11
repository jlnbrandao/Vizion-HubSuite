"""Unit tests for tenant Host / subdomain parsing and base-domain allowlist."""

from __future__ import annotations

import pytest

from src.shared.infrastructure.exceptions import ValidationError
from src.shared.infrastructure.tenant_host import (
    assert_host_base_domain_allowed,
    extract_tenant_slug_from_host,
)


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("universe.lanstar.com.br", "universe"),
        ("universe.lanstar.com.br:443", "universe"),
        ("universe.134.23.23.56", "universe"),
        ("universe.localhost", "universe"),
        ("universe.localhost:9000", "universe"),
        ("bigbang.localhost", "bigbang"),
        ("bigbang.134.209.122.250", "bigbang"),
        ("bigbang.lanstar.com.br", "bigbang"),
        ("bigbang.lanstar.local", "bigbang"),
        ("universe.lanstar.local", "universe"),
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
        "universe",
    ],
)
def test_extract_tenant_slug_rejects(host: str | None) -> None:
    with pytest.raises(ValidationError):
        extract_tenant_slug_from_host(host)


def test_base_domain_allowlist() -> None:
    assert_host_base_domain_allowed(
        "acme.lanstar.com.br",
        ("localhost", "lanstar.com.br", "lanstar.local"),
        enforce=True,
    )
    assert_host_base_domain_allowed(
        "bigbang.lanstar.local",
        ("localhost", "lanstar.com.br", "lanstar.local"),
        enforce=True,
    )
    assert_host_base_domain_allowed(
        "acme.10.0.0.1",
        ("localhost", "lanstar.com.br"),
        enforce=True,
    )
    with pytest.raises(ValidationError, match="not allowed"):
        assert_host_base_domain_allowed(
            "acme.evil.example",
            ("localhost", "lanstar.com.br", "lanstar.local"),
            enforce=True,
        )


def test_base_domain_allowlist_skipped_when_not_enforced() -> None:
    assert_host_base_domain_allowed(
        "acme.evil.example",
        ("localhost",),
        enforce=False,
    )
