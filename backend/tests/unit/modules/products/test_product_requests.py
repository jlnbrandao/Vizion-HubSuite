from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.config.settings import Settings
from src.modules.products.location import build_url, parse_endpoint
from src.modules.products.service import CreateInstanceRequest, ProductRegistryService
from src.shared.infrastructure.exceptions import ValidationError


def test_parse_endpoint_host_and_port() -> None:
    scheme, host, port = parse_endpoint("http://tracking-api:8000")
    assert scheme == "http"
    assert host == "tracking-api"
    assert port == 8000


def test_parse_endpoint_default_https_port() -> None:
    scheme, host, port = parse_endpoint("https://track.example.com/api")
    assert scheme == "https"
    assert host == "track.example.com"
    assert port == 443


def test_build_url_omits_default_port() -> None:
    assert build_url("https", "hub.example.com", 443) == "https://hub.example.com"
    assert build_url("http", "10.0.0.12", 8100) == "http://10.0.0.12:8100"


def test_create_accepts_base_url() -> None:
    body = CreateInstanceRequest(
        slug="tracking",
        name="Tracking A",
        base_url="http://tracking-api:8000",
        client_id="tracking-a",
        client_secret="super-secret-value",
    )
    assert body.slug == "tracking"
    assert body.base_url == "http://tracking-api:8000"


def test_create_accepts_host_and_port() -> None:
    body = CreateInstanceRequest(
        slug="tracking",
        name="Tracking A",
        client_id="tracking-a",
        client_secret="super-secret-value",
        environment="remote_vps",
        host="10.0.0.12",
        api_port=8100,
        ui_port=9100,
        notes="VPS cliente ACME",
    )
    assert body.environment == "remote_vps"
    assert body.host == "10.0.0.12"
    assert body.api_port == 8100


def test_create_rejects_short_secret() -> None:
    with pytest.raises(PydanticValidationError):
        CreateInstanceRequest(
            slug="tracking",
            name="Tracking A",
            client_id="tracking-a",
            client_secret="short",
            host="localhost",
            api_port=8100,
        )


def _registry() -> ProductRegistryService:
    return ProductRegistryService(Settings(), MagicMock())


def test_resolve_location_from_host_and_port() -> None:
    location = _registry()._resolve_location(
        environment="remote_vps",
        host="10.0.0.12",
        api_port=8100,
        ui_host="10.0.0.12",
        ui_port=9100,
        scheme="http",
        base_url="",
        ui_url=None,
        notes="VPS ACME",
    )
    assert location["base_url"] == "http://10.0.0.12:8100"
    assert location["ui_url"] == "http://10.0.0.12:9100"
    assert location["environment"] == "remote_vps"


def test_resolve_location_from_base_url() -> None:
    location = _registry()._resolve_location(
        environment="local_docker",
        host="",
        api_port=None,
        ui_host=None,
        ui_port=None,
        scheme="http",
        base_url="http://tracking-api:8000",
        ui_url="http://localhost:9100",
        notes="",
    )
    assert location["host"] == "tracking-api"
    assert location["api_port"] == 8000
    assert location["ui_host"] == "localhost"
    assert location["ui_port"] == 9100


def test_resolve_location_rejects_unknown_environment() -> None:
    with pytest.raises(ValidationError, match="Unknown environment"):
        _registry()._resolve_location(
            environment="on_prem_rack",
            host="localhost",
            api_port=8100,
            ui_host=None,
            ui_port=None,
            scheme="http",
            base_url="",
            ui_url=None,
            notes="",
        )
