"""Database provider — PostgreSQL read-only access (asyncpg, server-side only)."""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|"
    r"copy|call|do|execute|merge|replace|vacuum|refresh)\b",
    re.IGNORECASE,
)

ConnectFn = Callable[..., Awaitable[Any]]


class DatabaseProvider:
    """ETAPA 10: third-party DB access is SELECT-only; writes are rejected."""

    type = "database"

    def __init__(self, *, connect: ConnectFn | None = None) -> None:
        self._connect = connect or _default_connect

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        host = _cfg(configuration, "host")
        database = _cfg(configuration, "database")
        username = _cfg(configuration, "username")
        if not host or not database or not username:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Host, database ou usuário não configurados.",
            )
        if not _force_read_only(configuration):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Integração database exige read_only=true.",
            )
        password = _secret(secrets, "password", "db_password")
        if not password:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Senha do banco não configurada no backend.",
            )

        port = _port(configuration)
        started = time.perf_counter()
        conn: Any | None = None
        try:
            conn = await self._connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                timeout=_timeout_s(configuration),
                server_settings={"default_transaction_read_only": "on"},
            )
            one = await conn.fetchval("SELECT 1")
            read_only = await conn.fetchval("SHOW default_transaction_read_only")
            if one != 1:
                return IntegrationTestResult(
                    success=False,
                    message="Falha na conexão",
                    server=f"{host}:{port}/{database}",
                    authentication="DB credentials",
                    error_detail="Probe SELECT 1 falhou.",
                )
            if str(read_only).lower() not in {"on", "true", "1"}:
                return IntegrationTestResult(
                    success=False,
                    message="Falha na conexão",
                    server=f"{host}:{port}/{database}",
                    authentication="DB credentials",
                    error_detail="Sessão não está em modo read-only.",
                )
        except Exception as exc:  # noqa: BLE001 — surface safe DB errors
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=f"{host}:{port}/{database}",
                authentication="DB credentials",
                error_detail=_safe_db_error(exc),
            )
        finally:
            if conn is not None:
                await conn.close()

        duration_ms = int((time.perf_counter() - started) * 1000)
        schema = _cfg(configuration, "schema") or "public"
        return IntegrationTestResult(
            success=True,
            message="Conexão realizada com sucesso (somente leitura)",
            server=f"{host}:{port}/{database}",
            duration_ms=duration_ms,
            authentication="DB credentials",
            permission=f"SELECT only · schema={schema}",
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        host = _cfg(configuration, "host")
        database = _cfg(configuration, "database")
        username = _cfg(configuration, "username")
        if not host or not database or not username:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Host, database ou usuário não configurados.",
                started_at=started_at,
                finished_at=finished,
            )
        if not _force_read_only(configuration):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Integração database exige read_only=true.",
                started_at=started_at,
                finished_at=finished,
            )
        password = _secret(secrets, "password", "db_password")
        if not password:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Senha do banco não configurada no backend.",
                started_at=started_at,
                finished_at=finished,
            )

        try:
            sql, args = _build_read_query(configuration)
        except _DatabaseConfigError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=str(exc),
                started_at=started_at,
                finished_at=finished,
            )

        port = _port(configuration)
        conn: Any | None = None
        try:
            conn = await self._connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                timeout=_timeout_s(configuration),
                server_settings={"default_transaction_read_only": "on"},
            )
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(sql, *args)
        except Exception as exc:  # noqa: BLE001
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=_safe_db_error(exc),
                started_at=started_at,
                finished_at=finished,
            )
        finally:
            if conn is not None:
                await conn.close()

        finished = datetime.now(UTC).isoformat()
        count = len(rows)
        return IntegrationSyncResult(
            success=True,
            mode="full",
            records_processed=count,
            message=(
                f"DB read-only sync: {count} linha(s) de "
                f"{host}:{port}/{database}."
            ),
            started_at=started_at,
            finished_at=finished,
        )


class _DatabaseConfigError(Exception):
    """Safe configuration / SQL validation error."""


async def _default_connect(**kwargs: Any) -> Any:
    import asyncpg

    return await asyncpg.connect(**kwargs)


def _build_read_query(configuration: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build a SELECT-only query from table or validated custom query."""
    custom = _cfg(configuration, "query")
    row_limit = _row_limit(configuration)
    if custom:
        if ";" in custom.rstrip().rstrip(";"):
            raise _DatabaseConfigError("Query customizada não pode conter múltiplos statements.")
        stripped = custom.strip().rstrip(";")
        if not re.match(r"^(with|select)\b", stripped, re.IGNORECASE):
            raise _DatabaseConfigError("Query customizada deve começar com SELECT ou WITH.")
        if _FORBIDDEN_SQL.search(stripped):
            raise _DatabaseConfigError("Query customizada contém palavra-chave não permitida.")
        # Wrap to enforce LIMIT even if the query already has one — subquery form.
        sql = f"SELECT * FROM ({stripped}) AS _integration_read LIMIT $1"
        return sql, [row_limit]

    table = _cfg(configuration, "table")
    if not table:
        raise _DatabaseConfigError("Informe a tabela (ou uma query SELECT) para o sync.")
    schema = _cfg(configuration, "schema") or "public"
    if not _IDENT.match(schema) or not _IDENT.match(table):
        raise _DatabaseConfigError("Schema/tabela inválidos (use identificadores SQL simples).")
    sql = f'SELECT * FROM "{schema}"."{table}" LIMIT $1'
    return sql, [row_limit]


def _force_read_only(configuration: dict[str, Any]) -> bool:
    raw = configuration.get("read_only")
    if raw is None:
        raw = configuration.get("readOnly")
    if raw is None:
        return True  # default enforced
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _row_limit(configuration: dict[str, Any]) -> int:
    raw = (
        configuration.get("row_limit")
        or configuration.get("rowLimit")
        or configuration.get("page_size")
        or configuration.get("pageSize")
        or 1000
    )
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        limit = 1000
    return max(1, min(limit, 10_000))


def _port(configuration: dict[str, Any]) -> int:
    raw = configuration.get("port")
    try:
        port = int(raw) if raw is not None else 5432
    except (TypeError, ValueError):
        port = 5432
    return port if 1 <= port <= 65535 else 5432


def _timeout_s(configuration: dict[str, Any]) -> float:
    raw = configuration.get("timeout_ms") or configuration.get("timeoutMs") or 15_000
    try:
        return max(1.0, float(raw) / 1000.0)
    except (TypeError, ValueError):
        return 15.0


def _cfg(configuration: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = configuration.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _secret(secrets: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _safe_db_error(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    lowered = text.lower()
    for needle in ("password", "secret", "credential"):
        if needle in lowered:
            return type(exc).__name__
    return text[:300]
