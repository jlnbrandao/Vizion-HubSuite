"""IntegrationLayer — selects the protocol provider (Strategy)."""

from __future__ import annotations

from typing import Any

from src.modules.integrations.providers.base import (
    IntegrationProvider,
    IntegrationSyncResult,
    IntegrationTestResult,
)
from src.modules.integrations.providers.database_provider import DatabaseProvider
from src.modules.integrations.providers.http_file_provider import HttpFileProvider
from src.modules.integrations.providers.incremental_sync_provider import (
    IncrementalSyncProvider,
)
from src.modules.integrations.providers.mtls_provider import MTLSProvider
from src.modules.integrations.providers.oauth2_provider import OAuth2Provider
from src.modules.integrations.providers.rest_provider import RestProvider
from src.modules.integrations.providers.sftp_provider import SFTPProvider
from src.modules.integrations.providers.soap_provider import SoapProvider
from src.modules.integrations.providers.webhook_provider import WebhookProvider
from src.shared.infrastructure.exceptions import ValidationError


class IntegrationLayer:
    def __init__(self, providers: list[IntegrationProvider] | None = None) -> None:
        rest = RestProvider()
        registered = providers or [
            rest,
            OAuth2Provider(rest_provider=rest),
            MTLSProvider(),
            WebhookProvider(),
            SFTPProvider(),
            HttpFileProvider(),
            SoapProvider(),
            IncrementalSyncProvider(rest_provider=rest),
            DatabaseProvider(),
        ]
        self._providers: dict[str, IntegrationProvider] = {
            provider.type: provider for provider in registered
        }

    def get_provider(self, integration_type: str) -> IntegrationProvider:
        provider = self._providers.get(integration_type)
        if provider is None:
            available = ", ".join(sorted(self._providers))
            raise ValidationError(
                f"Provider '{integration_type}' ainda não está disponível. "
                f"Disponíveis: {available}."
            )
        return provider

    async def test_connection(
        self,
        *,
        integration_type: str,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        provider = self.get_provider(integration_type)
        return await provider.test_connection(
            configuration=configuration, secrets=secrets
        )

    async def sync(
        self,
        *,
        integration_type: str,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        provider = self.get_provider(integration_type)
        return await provider.sync(configuration=configuration, secrets=secrets)
