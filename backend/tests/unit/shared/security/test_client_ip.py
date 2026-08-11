"""Client IP helper tests."""

from __future__ import annotations

from starlette.requests import Request

from src.shared.infrastructure.security.client_ip import client_ip_from_request


def _request(headers: dict[str, str] | None = None, client: str | None = "9.9.9.9") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": (client, 12345) if client else None,
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_prefers_x_forwarded_for() -> None:
    req = _request({"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
    assert client_ip_from_request(req) == "1.2.3.4"


def test_falls_back_to_x_real_ip() -> None:
    req = _request({"x-real-ip": "5.6.7.8"})
    assert client_ip_from_request(req) == "5.6.7.8"


def test_falls_back_to_socket_peer() -> None:
    req = _request()
    assert client_ip_from_request(req) == "9.9.9.9"
