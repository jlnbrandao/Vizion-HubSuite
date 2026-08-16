"""Liveness vs readiness. Ready checks only dependencies the process needs to serve."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

HealthCheck = Callable[[], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    checks: dict[str, str]

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def liveness_payload(*, app: str, version: str) -> dict[str, str]:
    return {"status": "ok", "app": app, "version": version}


def version_payload(*, app: str, version: str, git_sha: str = "") -> dict[str, str]:
    payload = {"app": app, "version": version}
    if git_sha:
        payload["git_sha"] = git_sha
    return payload


async def readiness_payload(
    checks: dict[str, HealthCheck],
) -> tuple[dict[str, Any], int]:
    results: dict[str, str] = {}
    healthy = True
    for name, check in checks.items():
        try:
            ok = await check()
        except Exception:  # noqa: BLE001 — readiness must not raise
            ok = False
        results[name] = "ok" if ok else "fail"
        healthy = healthy and ok
    status = "ok" if healthy else "degraded"
    return {"status": status, "checks": results}, 200 if healthy else 503
