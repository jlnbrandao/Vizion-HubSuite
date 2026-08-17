from src.modules.services.catalog import ALL_SERVICES, PRODUCT_SERVICES


def test_distributed_products_are_sellable_not_core() -> None:
    slugs = {item.slug for item in PRODUCT_SERVICES}
    assert slugs == {"tracking", "iot", "snmp", "gis", "lanstar"}
    for item in PRODUCT_SERVICES:
        assert item.is_core is False
        assert item.tenant_only is True
        assert item.enabled_by_default is False
    assert all(item in ALL_SERVICES for item in PRODUCT_SERVICES)
