"""Unit tests for SoapProvider."""

from __future__ import annotations

import httpx
import pytest

from src.modules.integrations.providers.soap_provider import SoapProvider

_WSDL = """<?xml version="1.0"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/">
  <portType name="AddressPort">
    <operation name="ListAddresses"/>
  </portType>
</definitions>
"""

_SOAP_OK = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ListAddressesResponse xmlns="urn:integration">
      <Address><id>1</id></Address>
      <Address><id>2</id></Address>
    </ListAddressesResponse>
  </soap:Body>
</soap:Envelope>
"""

_SOAP_FAULT = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>Boom</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>
"""


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_soap_test_connection_finds_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, text=_WSDL, headers={"content-type": "text/xml"})

    _patch_client(monkeypatch, handler)
    provider = SoapProvider()
    result = await provider.test_connection(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "ListAddresses",
            "auth_type": "none",
        },
        secrets={},
    )
    assert result.success is True
    assert result.permission == "ListAddresses"
    assert result.server == "soap.example.com"


@pytest.mark.asyncio
async def test_soap_test_connection_missing_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_WSDL)

    _patch_client(monkeypatch, handler)
    provider = SoapProvider()
    result = await provider.test_connection(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "DeleteEverything",
        },
        secrets={},
    )
    assert result.success is False
    assert "DeleteEverything" in (result.error_detail or "")


@pytest.mark.asyncio
async def test_soap_sync_counts_records(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/service"
        assert "ListAddresses" in request.headers.get("SOAPAction", "")
        body = request.content.decode()
        assert "ListAddresses" in body
        assert "soap:Envelope" in body
        return httpx.Response(200, text=_SOAP_OK, headers={"content-type": "text/xml"})

    _patch_client(monkeypatch, handler)
    provider = SoapProvider()
    result = await provider.sync(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "ListAddresses",
            "namespace": "urn:integration",
        },
        secrets={},
    )
    assert result.success is True
    assert result.records_processed == 2


@pytest.mark.asyncio
async def test_soap_sync_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_SOAP_FAULT)

    _patch_client(monkeypatch, handler)
    provider = SoapProvider()
    result = await provider.sync(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "ListAddresses",
        },
        secrets={},
    )
    assert result.success is False
    assert "Boom" in result.message


@pytest.mark.asyncio
async def test_soap_basic_auth_required() -> None:
    provider = SoapProvider()
    result = await provider.test_connection(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "ListAddresses",
            "auth_type": "basic",
        },
        secrets={},
    )
    assert result.success is False
    assert "senha" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_soap_bearer_header(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer soap-tok"
        return httpx.Response(200, text=_WSDL)

    _patch_client(monkeypatch, handler)
    provider = SoapProvider()
    result = await provider.test_connection(
        configuration={
            "wsdl_url": "https://soap.example.com/service?wsdl",
            "operation": "ListAddresses",
            "auth_type": "bearer",
        },
        secrets={"bearer_token": "soap-tok"},
    )
    assert result.success is True
    assert result.authentication == "SOAP Bearer"
