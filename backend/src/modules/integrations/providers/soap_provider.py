"""SOAP outbound provider — WSDL probe + SOAP 1.1 call (httpx, server-side only)."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse, urlunparse
from xml.etree import ElementTree as ET

import httpx

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)
from src.modules.integrations.providers.rest_provider import _safe_error, _safe_host

_SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
_SOAP_NS = {"soap": _SOAP_ENV}


class SoapProvider:
    """ETAPA 8: fetch WSDL, invoke operation via SOAPAction / envelope."""

    type = "soap"

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.4,
    ) -> None:
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        wsdl_url = _cfg(configuration, "wsdl_url", "wsdlUrl")
        operation = _cfg(configuration, "operation")
        if not wsdl_url or not operation:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="WSDL ou operação SOAP não configurados.",
            )
        if err := _url_scheme_error(wsdl_url):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=err,
            )
        if err := _missing_auth_secret(configuration, secrets):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=err,
            )

        auth_label = _auth_label(configuration)
        started = time.perf_counter()
        try:
            response = await self._request(
                method="GET",
                url=wsdl_url,
                configuration=configuration,
                secrets=secrets,
                headers={"Accept": "application/xml, text/xml, */*"},
            )
        except httpx.TimeoutException:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(wsdl_url),
                authentication=auth_label,
                error_detail="Timeout ao contactar o WSDL.",
            )
        except httpx.HTTPError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(wsdl_url),
                authentication=auth_label,
                error_detail=_safe_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(wsdl_url),
                duration_ms=duration_ms,
                authentication=auth_label,
                error_detail=f"HTTP {response.status_code} ao buscar WSDL",
            )

        body = response.text or ""
        if not _looks_like_wsdl(body):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(wsdl_url),
                duration_ms=duration_ms,
                authentication=auth_label,
                error_detail="Resposta não parece um documento WSDL/XML.",
            )
        if not _wsdl_has_operation(body, operation):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(wsdl_url),
                duration_ms=duration_ms,
                authentication=auth_label,
                error_detail=f"Operação '{operation}' não encontrada no WSDL.",
            )

        return IntegrationTestResult(
            success=True,
            message="WSDL acessível e operação localizada",
            server=_safe_host(wsdl_url),
            duration_ms=duration_ms,
            authentication=auth_label,
            permission=operation,
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        wsdl_url = _cfg(configuration, "wsdl_url", "wsdlUrl")
        operation = _cfg(configuration, "operation")
        if not wsdl_url or not operation:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="WSDL ou operação SOAP não configurados.",
                started_at=started_at,
                finished_at=finished,
            )
        if err := _missing_auth_secret(configuration, secrets):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=err,
                started_at=started_at,
                finished_at=finished,
            )

        endpoint = _cfg(configuration, "endpoint") or _service_url_from_wsdl(wsdl_url)
        soap_action = _cfg(configuration, "soap_action", "soapAction")
        namespace = _cfg(configuration, "namespace") or "urn:integration"
        envelope = _build_envelope(operation=operation, namespace=namespace)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "Accept": "text/xml, application/xml, */*",
        }
        if soap_action:
            headers["SOAPAction"] = f'"{soap_action}"'
        else:
            headers["SOAPAction"] = f'"{operation}"'

        try:
            response = await self._request(
                method="POST",
                url=endpoint,
                configuration=configuration,
                secrets=secrets,
                headers=headers,
                content=envelope.encode("utf-8"),
            )
        except httpx.TimeoutException:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Timeout na chamada SOAP.",
                started_at=started_at,
                finished_at=finished,
            )
        except httpx.HTTPError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=_safe_error(exc),
                started_at=started_at,
                finished_at=finished,
            )

        finished = datetime.now(UTC).isoformat()
        if response.status_code >= 400:
            fault = _extract_fault(response.text or "")
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=fault or f"HTTP {response.status_code} na chamada SOAP.",
                started_at=started_at,
                finished_at=finished,
            )

        fault = _extract_fault(response.text or "")
        if fault:
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=fault,
                started_at=started_at,
                finished_at=finished,
            )

        records = _count_body_records(response.text or "")
        return IntegrationSyncResult(
            success=True,
            mode="full",
            records_processed=records,
            message=(
                f"SOAP '{operation}' OK em {_safe_host(endpoint)}; "
                f"{records} registro(s) no Body."
            ),
            started_at=started_at,
            finished_at=finished,
        )

    async def _request(
        self,
        *,
        method: str,
        url: str,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
        headers: dict[str, str],
        content: bytes | None = None,
    ) -> httpx.Response:
        timeout_ms = configuration.get("timeout_ms") or configuration.get("timeoutMs")
        try:
            timeout_s = max(1.0, float(timeout_ms) / 1000.0) if timeout_ms else 30.0
        except (TypeError, ValueError):
            timeout_s = 30.0

        req_headers = dict(headers)
        auth = _httpx_auth(configuration, secrets)
        _apply_bearer(req_headers, configuration, secrets)

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_s, follow_redirects=True, auth=auth
                ) as client:
                    response = await client.request(
                        method, url, headers=req_headers, content=content
                    )
                if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < (
                    self._max_retries
                ):
                    await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue
                return response
            except httpx.TimeoutException:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt + 1 >= self._max_retries:
                    raise
                await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
        assert last_exc is not None
        raise last_exc


def _build_envelope(*, operation: str, namespace: str) -> str:
    # Minimal document/literal-style body — payload binding can be extended later.
    op = _xml_local_name(operation)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap:Envelope xmlns:soap="{_SOAP_ENV}">'
        "<soap:Body>"
        f'<{op} xmlns="{namespace}"/>'
        "</soap:Body>"
        "</soap:Envelope>"
    )


def _looks_like_wsdl(text: str) -> bool:
    lowered = text.lower()
    return "<definitions" in lowered or "wsdl:" in lowered or ":definitions" in lowered


def _wsdl_has_operation(text: str, operation: str) -> bool:
    op = _xml_local_name(operation)
    # Match name="Op" or name='Op' in operation elements.
    pattern = re.compile(
        rf'<\s*(?:\w+:)?operation\b[^>]*\bname\s*=\s*["\']{re.escape(op)}["\']',
        re.IGNORECASE,
    )
    return bool(pattern.search(text)) or op in text


def _extract_fault(text: str) -> str | None:
    if not text.strip():
        return None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        if "fault" in text.lower():
            return "SOAP Fault (XML inválido na resposta)"
        return None

    fault = root.find(".//soap:Fault", _SOAP_NS)
    if fault is None:
        # Namespace-agnostic fallback
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1].lower() == "fault":
                fault = el
                break
    if fault is None:
        return None

    faultstring = None
    for child in list(fault):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local == "faultstring" and child.text:
            faultstring = child.text.strip()
            break
    return f"SOAP Fault: {faultstring or 'erro remoto'}"


def _count_body_records(text: str) -> int:
    if not text.strip():
        return 0
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return 0

    body = root.find("soap:Body", _SOAP_NS)
    if body is None:
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1].lower() == "body":
                body = el
                break
    if body is None:
        return 0

    # Skip Fault; count direct children of first response element, else response itself.
    children = [
        c
        for c in list(body)
        if c.tag.rsplit("}", 1)[-1].lower() != "fault"
    ]
    if not children:
        return 0
    response_el = children[0]
    nested = list(response_el)
    if not nested:
        return 1
    # Prefer homogeneous repeating siblings as records.
    names = [c.tag.rsplit("}", 1)[-1] for c in nested]
    if len(names) > 1 and len(set(names)) == 1:
        return len(nested)
    return len(nested)


def _service_url_from_wsdl(wsdl_url: str) -> str:
    parsed = urlparse(wsdl_url)
    query = parsed.query
    if query.lower() in {"wsdl", "wsdl=1"} or "wsdl" in query.lower():
        return urlunparse(parsed._replace(query="", fragment=""))
    if parsed.path.lower().endswith(".wsdl"):
        return urlunparse(parsed._replace(path=parsed.path[: -len(".wsdl")], query=""))
    return wsdl_url


def _httpx_auth(
    configuration: dict[str, Any], secrets: dict[str, Any]
) -> httpx.Auth | None:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "none"
    ).strip().lower()
    if auth_type != "basic":
        return None
    username = _secret(secrets, "username", "user")
    password = _secret(secrets, "password")
    if username:
        return httpx.BasicAuth(username, password)
    return None


def _apply_bearer(
    headers: dict[str, str],
    configuration: dict[str, Any],
    secrets: dict[str, Any],
) -> None:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "none"
    ).strip().lower()
    if auth_type != "bearer":
        return
    token = _secret(secrets, "bearer_token", "access_token", "token")
    if token:
        headers["Authorization"] = f"Bearer {token}"


def _missing_auth_secret(
    configuration: dict[str, Any], secrets: dict[str, Any]
) -> str | None:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "none"
    ).strip().lower()
    if auth_type == "basic" and (
        not _secret(secrets, "username", "user") or not _secret(secrets, "password")
    ):
        return "Usuário/senha SOAP não configurados no backend."
    if auth_type == "bearer" and not _secret(
        secrets, "bearer_token", "access_token", "token"
    ):
        return "Bearer token SOAP não configurado no backend."
    return None


def _auth_label(configuration: dict[str, Any]) -> str:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "none"
    ).strip().lower()
    if auth_type == "basic":
        return "SOAP Basic"
    if auth_type == "bearer":
        return "SOAP Bearer"
    return "SOAP"


def _url_scheme_error(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return "URL WSDL inválida."
    if parsed.scheme not in {"http", "https"}:
        return "URL WSDL deve usar http ou https."
    if not parsed.netloc:
        return "URL WSDL inválida."
    return None


def _xml_local_name(name: str) -> str:
    cleaned = name.strip().split(":")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "", cleaned)
    return cleaned or "Operation"


def _cfg(configuration: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = configuration.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _secret(secrets: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
