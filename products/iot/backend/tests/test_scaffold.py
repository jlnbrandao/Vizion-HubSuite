from fastapi.testclient import TestClient

from openvizion.kernel.configuration import AdapterSelection, DeploymentMode
from openvizion.kernel.hub import HubPlatformAdapter
from iot.config import Settings
from iot.main import create_app


def test_standalone_health_and_no_hub() -> None:
    settings = Settings(
        deployment_mode=DeploymentMode.STANDALONE,
        platform_adapter=AdapterSelection.LOCAL,
        platform_core_url="",
    )
    app = create_app(settings)
    assert app.state.hub is None
    assert not isinstance(app.state.hub, HubPlatformAdapter)
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        version = client.get("/version")
        status = client.get("/api/v1/status")
    assert health.status_code == 200
    assert ready.status_code == 200
    assert version.json()["app"] == "OpenVizion IoT"
    assert status.json()["mode"] == "standalone"


def test_standalone_rejects_hub_url() -> None:
    settings = Settings(
        deployment_mode=DeploymentMode.STANDALONE,
        platform_adapter=AdapterSelection.LOCAL,
        platform_core_url="http://platform-core:8000",
    )
    try:
        create_app(settings)
    except ValueError as exc:
        assert "PLATFORM_CORE_URL" in str(exc)
    else:
        raise AssertionError("expected isolation error")
