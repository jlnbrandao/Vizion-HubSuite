from decimal import Decimal

from src.modules.billing.pricing import (
    USER_MONTHLY_BRL,
    is_included_service,
    normalize_promo,
    promo_discount,
    service_monthly_price,
)


def test_included_hub_services_are_free() -> None:
    assert is_included_service("iam")
    assert is_included_service("billing")
    assert service_monthly_price("iam") == Decimal("0.00")
    assert service_monthly_price("billing") == Decimal("0.00")


def test_integration_has_a_standard_price() -> None:
    assert service_monthly_price("integration") == Decimal("49.90")
    assert not is_included_service("integration")


def test_unknown_service_uses_the_default_price() -> None:
    assert service_monthly_price("gps", "standard") == Decimal("29.90")


def test_promo_codes_are_normalized() -> None:
    assert normalize_promo("vizion10") == "VIZION10"
    assert normalize_promo("unknown") is None
    assert promo_discount("LAUNCH20") == Decimal("20.00")
    assert promo_discount(None) == Decimal("0.00")
    assert Decimal("12.00") == USER_MONTHLY_BRL
