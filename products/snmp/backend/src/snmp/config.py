"""SNMP product settings. Adapter choice happens only here / in main."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from openvizion.kernel.configuration import AdapterSelection, DeploymentMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "OpenVizion SNMP"
    app_version: str = "0.1.0"
    service_name: str = "snmp"
    app_debug: bool = True

    deployment_mode: DeploymentMode = DeploymentMode.STANDALONE
    platform_adapter: AdapterSelection = AdapterSelection.LOCAL
    platform_core_url: str = ""
    platform_client_id: str = ""
    platform_client_secret: str = ""

    def validate_mode(self) -> None:
        if self.deployment_mode == DeploymentMode.STANDALONE:
            if self.platform_adapter != AdapterSelection.LOCAL:
                raise ValueError("DEPLOYMENT_MODE=standalone requires PLATFORM_ADAPTER=local")
            if self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=standalone forbids PLATFORM_CORE_URL")
        else:
            if self.platform_adapter != AdapterSelection.HUB:
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_ADAPTER=hub")
            if not self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_CORE_URL")
