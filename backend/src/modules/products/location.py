"""Where a product process is reachable — host, port, environment label."""

from __future__ import annotations

from urllib.parse import urlparse

ENVIRONMENTS: tuple[str, ...] = (
    "local_docker",
    "local_vps",
    "remote_docker",
    "remote_vps",
    "cloud",
)

ENVIRONMENT_LABELS: dict[str, str] = {
    "local_docker": "Local Docker",
    "local_vps": "Local VPS",
    "remote_docker": "Remote Docker",
    "remote_vps": "Remote VPS",
    "cloud": "Cloud",
    "in_process": "In-process (Hub)",
}


def default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def parse_endpoint(url: str) -> tuple[str, str, int]:
    """Return (scheme, host, port) from an http(s) URL."""
    parsed = urlparse((url or "").strip())
    scheme = (parsed.scheme or "http").lower()
    if scheme not in {"http", "https"}:
        scheme = "http"
    host = (parsed.hostname or "").strip().lower()
    port = parsed.port if parsed.port is not None else default_port(scheme)
    return scheme, host, port


def build_url(scheme: str, host: str, port: int) -> str:
    scheme = (scheme or "http").lower()
    host = host.strip()
    if not host:
        raise ValueError("host is required")
    if port in {80, 443} and (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"
