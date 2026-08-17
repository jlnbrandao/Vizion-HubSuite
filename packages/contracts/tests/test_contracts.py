from uuid import uuid4

from openvizion.contracts.events import EventEnvelope
from openvizion.contracts.products import PRODUCT_SLUGS, CreateProductInstanceRequest


def test_event_envelope_json() -> None:
    envelope = EventEnvelope(
        event_type="tracking.DeviceOffline",
        tenant_id=uuid4(),
        payload={"device_imei": "123"},
        producer="tracking",
    )
    data = envelope.to_dict()
    assert data["event_type"] == "tracking.DeviceOffline"
    assert "event_id" in data
    assert data["producer"] == "tracking"


def test_product_slugs() -> None:
    assert PRODUCT_SLUGS == ("tracking", "iot", "snmp", "gis", "lanstar")
    req = CreateProductInstanceRequest(
        slug="tracking",
        name="Tracking A",
        base_url="http://tracking-api:8000",
        client_id="tracking-a",
        client_secret="super-secret-value",
    )
    assert req.slug == "tracking"
