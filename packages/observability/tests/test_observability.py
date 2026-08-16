from openvizion.observability.health import liveness_payload, readiness_payload, version_payload
from openvizion.observability.context import bind_context, get_context, reset_context


def test_liveness_and_version() -> None:
    live = liveness_payload(app="tracking", version="0.1.0")
    assert live["status"] == "ok"
    ver = version_payload(app="tracking", version="0.1.0", git_sha="abc")
    assert ver["git_sha"] == "abc"


async def test_readiness_fails_only_needed_deps() -> None:
    async def postgres() -> bool:
        return True

    async def redis() -> bool:
        return False

    body, status = await readiness_payload({"postgres": postgres, "redis": redis})
    assert status == 503
    assert body["checks"]["postgres"] == "ok"
    assert body["checks"]["redis"] == "fail"


def test_correlation_context() -> None:
    token, ctx = bind_context(request_id="r1", correlation_id="c1", tenant_id="t1", service="tracking")
    try:
        current = get_context()
        assert current is not None
        assert current.request_id == "r1"
        assert current.as_log_fields()["service"] == "tracking"
        assert ctx.correlation_id == "c1"
    finally:
        reset_context(token)
    assert get_context() is None
