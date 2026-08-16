"""Deployment mode and adapter selection — composition root only."""

from __future__ import annotations

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(StrEnum):
    STANDALONE = "standalone"
    INTEGRATED = "integrated"


class AdapterSelection(StrEnum):
    LOCAL = "local"
    HUB = "hub"
    KAFKA = "kafka"


class KernelSettings(BaseSettings):
    """Subset of product settings that select adapters. Secrets stay in env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    deployment_mode: DeploymentMode = DeploymentMode.STANDALONE
    platform_adapter: AdapterSelection = AdapterSelection.LOCAL
    platform_core_url: str = ""
    platform_client_id: str = ""
    platform_client_secret: str = ""
    event_bus_adapter: AdapterSelection = AdapterSelection.LOCAL
    kafka_bootstrap_servers: str = ""
    kafka_topic_prefix: str = "openvizion"
    storage_adapter: AdapterSelection = AdapterSelection.LOCAL

    def require_standalone_isolation(self) -> None:
        """Standalone must never point at a remote Platform Core."""
        if self.deployment_mode == DeploymentMode.STANDALONE:
            if self.platform_adapter != AdapterSelection.LOCAL:
                raise ValueError("DEPLOYMENT_MODE=standalone requires PLATFORM_ADAPTER=local")
            if self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=standalone forbids PLATFORM_CORE_URL")

    def require_integrated_hub(self) -> None:
        if self.deployment_mode == DeploymentMode.INTEGRATED:
            if self.platform_adapter != AdapterSelection.HUB:
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_ADAPTER=hub")
            if not self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_CORE_URL")
