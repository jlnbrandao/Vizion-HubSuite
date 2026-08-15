from src.modules.services.catalog import (
    CORE_SERVICES,
    PLATFORM_TENANT_SLUG,
    ServiceDefinition,
)


def test_billing_is_tenant_only_and_on_by_default() -> None:
    billing = next(item for item in CORE_SERVICES if item.slug == "billing")
    assert billing.tenant_only is True
    assert billing.enabled_by_default is True
    assert billing.is_core is False
    assert PLATFORM_TENANT_SLUG == "ows"


def test_hub_services_are_not_tenant_only() -> None:
    for item in CORE_SERVICES:
        if item.slug == "billing":
            continue
        assert item.tenant_only is False


def test_service_definition_defaults_tenant_only_off() -> None:
    item = ServiceDefinition(slug="gps", namespace="gps", name="GPS", description="")
    assert item.tenant_only is False
