"""Asaas HTTP client. The API key never leaves the backend."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from src.config.settings import Settings
from src.shared.infrastructure.exceptions import (
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)

ASAAS_STATUS_MAP: dict[str, str] = {
    "PENDING": "pending",
    "AWAITING_RISK_ANALYSIS": "pending",
    "CONFIRMED": "paid",
    "RECEIVED": "paid",
    "RECEIVED_IN_CASH": "paid",
    "OVERDUE": "overdue",
    "REFUNDED": "cancelled",
    "REFUND_REQUESTED": "cancelled",
    "CHARGEBACK_REQUESTED": "cancelled",
    "CHARGEBACK_DISPUTE": "cancelled",
    "AWAITING_CHARGEBACK_REVERSAL": "cancelled",
    "DUNNING_REQUESTED": "overdue",
    "DUNNING_RECEIVED": "paid",
    "DELETED": "cancelled",
}


def map_asaas_status(status: str | None) -> str:
    if not status:
        return "pending"
    return ASAAS_STATUS_MAP.get(status.upper(), "pending")


class AsaasClient:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.asaas_api_key.strip()
        self._base_url = settings.asaas_base_url.rstrip("/")
        self._webhook_token = settings.asaas_webhook_token.strip()

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def require_configured(self) -> None:
        if not self.configured:
            raise ServiceUnavailableError("Asaas is not configured")

    def verify_webhook(self, token: str | None) -> None:
        if not self._webhook_token:
            raise ServiceUnavailableError("Asaas webhook token is not configured")
        if not token or token != self._webhook_token:
            raise UnauthorizedError("Invalid Asaas webhook token")

    async def create_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/customers", json=payload)

    async def update_customer(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/customers/{customer_id}", json=payload)

    async def tokenize_card(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/creditCard/tokenizeCreditCard", json=payload)

    async def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/payments", json=payload)

    async def _request(self, method: str, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        self.require_configured()
        url = f"{self._base_url}{path}"
        headers = {"access_token": self._api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(method, url, headers=headers, json=json)
        if response.status_code >= 400:
            detail = _asaas_error(response)
            if response.status_code == 401:
                raise UnauthorizedError(detail)
            raise ValidationError(detail)
        data = response.json()
        if not isinstance(data, dict):
            raise ValidationError("Unexpected Asaas response")
        return data


def money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _asaas_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"Asaas error ({response.status_code})"
    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict) and first.get("description"):
            return str(first["description"])
    return f"Asaas error ({response.status_code})"
