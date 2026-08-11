"""Extract tenant slug from HTTP Host (subdomain = first label)."""

from __future__ import annotations

import re

from src.shared.infrastructure.exceptions import ValidationError

_RESERVED_LABELS = frozenset(
    {
        "www",
        "api",
        "localhost",
        "127",
        "health",
        "static",
        "assets",
    }
)

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def normalize_host(host_header: str | None) -> str:
    if not host_header:
        raise ValidationError("Missing Host header")
    host = host_header.strip().lower()
    if not host:
        raise ValidationError("Missing Host header")
    # Strip port (keep IPv6 bracket form unsupported for tenant hosts).
    if host.startswith("["):
        raise ValidationError("Invalid Host for tenant resolution")
    host = host.split(":", 1)[0]
    return host


def _base_domain(host: str) -> str:
    labels = [part for part in host.split(".") if part]
    return ".".join(labels[1:]) if len(labels) >= 2 else ""


def assert_host_base_domain_allowed(
    host_header: str | None,
    allowed_base_domains: tuple[str, ...] | list[str],
    *,
    enforce: bool,
) -> None:
    """Reject Hosts whose suffix is not in the allowlist when enforce=True."""
    if not enforce:
        return
    allowed = tuple(d.strip().lower() for d in allowed_base_domains if d and d.strip())
    if not allowed:
        raise ValidationError("No allowed tenant base domains configured")

    host = normalize_host(host_header)
    if _IPV4_RE.match(host) or host == "localhost":
        raise ValidationError(
            "Tenant subdomain required (e.g. universe.localhost or universe.lanstar.com.br)"
        )

    base = _base_domain(host)
    if not base:
        raise ValidationError(
            "Tenant subdomain required (e.g. universe.localhost or universe.lanstar.com.br)"
        )

    # Allow exact base match or IP second-label form (universe.10.0.0.1 → base 10.0.0.1).
    if base in allowed:
        return
    if _IPV4_RE.match(base):
        return
    raise ValidationError(f"Host base domain not allowed: {base}")


def extract_tenant_slug_from_host(host_header: str | None) -> str:
    """Return tenant slug from Host first label.

    Examples:
      universe.lanstar.com.br → universe
      universe.134.23.23.56 → universe
      universe.localhost → universe
      bigbang.localhost → bigbang
    """
    host = normalize_host(host_header)

    if _IPV4_RE.match(host) or host == "localhost":
        raise ValidationError(
            "Tenant subdomain required (e.g. universe.localhost or universe.lanstar.com.br)"
        )

    labels = [part for part in host.split(".") if part]
    if len(labels) < 2:
        raise ValidationError(
            "Tenant subdomain required (e.g. universe.localhost or universe.lanstar.com.br)"
        )

    slug = labels[0]
    if slug in _RESERVED_LABELS:
        raise ValidationError(f"Reserved tenant slug: {slug}")
    if not _SLUG_RE.match(slug):
        raise ValidationError(f"Invalid tenant slug: {slug}")
    return slug
