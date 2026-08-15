from datetime import UTC, datetime

import pytest

from src.config.settings import Settings
from src.modules.billing.asaas import AsaasClient, map_asaas_status
from src.modules.billing.service import current_period
from src.shared.infrastructure.exceptions import ServiceUnavailableError, UnauthorizedError


def test_asaas_status_mapping() -> None:
    assert map_asaas_status("CONFIRMED") == "paid"
    assert map_asaas_status("RECEIVED") == "paid"
    assert map_asaas_status("OVERDUE") == "overdue"
    assert map_asaas_status("PENDING") == "pending"
    assert map_asaas_status(None) == "pending"
    assert map_asaas_status("UNKNOWN") == "pending"


def test_unconfigured_client_refuses_live_calls() -> None:
    client = AsaasClient(Settings(asaas_api_key=""))
    assert client.configured is False
    with pytest.raises(ServiceUnavailableError):
        client.require_configured()


def test_webhook_token_is_checked() -> None:
    client = AsaasClient(Settings(asaas_api_key="k", asaas_webhook_token="secret"))
    with pytest.raises(UnauthorizedError):
        client.verify_webhook("wrong")
    client.verify_webhook("secret")


def test_current_period_uses_the_close_day() -> None:
    now = datetime(2026, 8, 15, tzinfo=UTC)
    start, end = current_period(now, 9)
    assert start.day == 9
    assert start.month == 8
    assert end.day == 9
    assert end.month == 9

    early = datetime(2026, 8, 5, tzinfo=UTC)
    start, end = current_period(early, 9)
    assert start.month == 7
    assert end.month == 8
