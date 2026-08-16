"""JSON structured logging with correlation fields."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from openvizion.observability.context import get_context

_SECRET_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "client_secret",
        "api_key",
        "jwt",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        ctx = get_context()
        if ctx is not None:
            payload.update(ctx.as_log_fields())
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
            and key not in {"message", "msg", "args"}
        }
        for key, value in extra.items():
            if key.lower() in _SECRET_KEYS:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_json_logging(*, level: int = logging.INFO, service: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    if service:
        logging.LoggerAdapter(root, {"service": service})


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
