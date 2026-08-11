"""Client IP extraction for rate limiting behind reverse proxies."""

from __future__ import annotations

from starlette.requests import Request


def client_ip_from_request(request: Request) -> str:
    """Prefer nginx ``X-Real-IP`` ($remote_addr); never trust the first XFF hop.

    ``X-Forwarded-For`` may include a client-supplied prefix when the proxy uses
    ``$proxy_add_x_forwarded_for``. Using the first hop enables rate-limit bypass.
    Prefer ``X-Real-IP`` (set by nginx to the connecting peer). If only XFF is
    present, use the *last* hop (closest to the trusted proxy).
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or "unknown"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        hops = [part.strip() for part in forwarded.split(",") if part.strip()]
        if hops:
            return hops[-1]

    if request.client and request.client.host:
        return request.client.host
    return "unknown"
