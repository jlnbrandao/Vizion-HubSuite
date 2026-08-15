"""Declarative monthly prices in BRL for contracted services and active users."""

from __future__ import annotations

from decimal import Decimal

USER_MONTHLY_BRL = Decimal("12.00")

#: (service_slug, plan) → monthly amount. Missing keys default to SERVICE_DEFAULT.
SERVICE_PRICES: dict[tuple[str, str], Decimal] = {
    ("iam", "standard"): Decimal("0.00"),
    ("platform", "standard"): Decimal("0.00"),
    ("billing", "standard"): Decimal("0.00"),
    ("integration", "standard"): Decimal("49.90"),
}

SERVICE_DEFAULT = Decimal("29.90")

PROMO_CODES: dict[str, Decimal] = {
    "VIZION10": Decimal("10.00"),
    "LAUNCH20": Decimal("20.00"),
}

INCLUDED_SERVICE_SLUGS: frozenset[str] = frozenset({"iam", "platform", "billing"})


def service_monthly_price(slug: str, plan: str = "standard") -> Decimal:
    return SERVICE_PRICES.get((slug, plan), SERVICE_DEFAULT)


def is_included_service(slug: str) -> bool:
    return slug in INCLUDED_SERVICE_SLUGS


def promo_discount(code: str | None) -> Decimal:
    if not code:
        return Decimal("0.00")
    return PROMO_CODES.get(code.strip().upper(), Decimal("0.00"))


def normalize_promo(code: str) -> str | None:
    cleaned = code.strip().upper()
    if not cleaned:
        return None
    if cleaned not in PROMO_CODES:
        return None
    return cleaned
