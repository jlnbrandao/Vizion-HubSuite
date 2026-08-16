"""Standalone composition never instantiates HubPlatformAdapter."""

from openvizion.kernel.configuration import AdapterSelection, DeploymentMode
from openvizion.kernel.hub import HubPlatformAdapter
from openvizion.kernel.local import LocalPlatformAdapter
from tracking.config import Settings
from tracking.infrastructure.composition import build_container


def test_standalone_uses_local_adapter_only(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_MODE", "standalone")
    monkeypatch.setenv("PLATFORM_ADAPTER", "local")
    monkeypatch.setenv("PLATFORM_CORE_URL", "")
    monkeypatch.setenv("EVENT_BUS_ADAPTER", "local")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://tracking:tracking@localhost:5432/tracking")
    Settings.model_config["env_file"] = None
    settings = Settings(
        deployment_mode=DeploymentMode.STANDALONE,
        platform_adapter=AdapterSelection.LOCAL,
        platform_core_url="",
        event_bus_adapter=AdapterSelection.LOCAL,
        database_url="postgresql+asyncpg://tracking:tracking@localhost:5432/tracking",
    )
    container = build_container(settings)
    assert container.hub is None
    assert isinstance(container.platform, LocalPlatformAdapter)
    assert not isinstance(container.platform, HubPlatformAdapter)
