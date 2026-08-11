"""Client IP extraction for rate limiting behind reverse proxies."""

from __future__ import annotations

from starlette.requests import Request


def client_ip_from_request(request: Request) -> str:
    """Prefer trusted proxy headers, then socket peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First hop is the original client when nginx appends correctly.
        return forwarded.split(",", 1)[0].strip() or "unknown"
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
