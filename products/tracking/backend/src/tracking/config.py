"""Tracking product settings. Secrets come from the environment only."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from openvizion.kernel.configuration import AdapterSelection, DeploymentMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "OpenVizion Tracking"
    app_env: str = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"
    service_name: str = "tracking"

    deployment_mode: DeploymentMode = DeploymentMode.STANDALONE
    platform_adapter: AdapterSelection = AdapterSelection.LOCAL
    platform_core_url: str = ""
    platform_client_id: str = ""
    platform_client_secret: str = ""
    platform_timeout_seconds: float = 5.0

    event_bus_adapter: AdapterSelection = AdapterSelection.LOCAL
    kafka_bootstrap_servers: str = ""
    kafka_topic_prefix: str = "openvizion"

    database_url: str = "postgresql+asyncpg://tracking:tracking@localhost:5432/tracking"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production-tracking-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    allowed_tenant_base_domains: str = "localhost,openvizion.com,openvizion.local"
    seed_allow_insecure: bool = False

    worker_poll_seconds: float = 2.0
    position_queue_key: str = "tracking:positions"

    @property
    def tenant_base_domains(self) -> tuple[str, ...]:
        return tuple(
            item.strip().lower()
            for item in self.allowed_tenant_base_domains.split(",")
            if item.strip()
        )

    @property
    def is_standalone(self) -> bool:
        return self.deployment_mode == DeploymentMode.STANDALONE

    def validate_mode(self) -> None:
        if self.is_standalone:
            if self.platform_adapter != AdapterSelection.LOCAL:
                raise ValueError("DEPLOYMENT_MODE=standalone requires PLATFORM_ADAPTER=local")
            if self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=standalone forbids PLATFORM_CORE_URL")
        else:
            if self.platform_adapter != AdapterSelection.HUB:
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_ADAPTER=hub")
            if not self.platform_core_url.strip():
                raise ValueError("DEPLOYMENT_MODE=integrated requires PLATFORM_CORE_URL")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_mode()
    return settings
