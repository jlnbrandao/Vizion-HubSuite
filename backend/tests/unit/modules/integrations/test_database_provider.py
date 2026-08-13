"""Unit tests for DatabaseProvider (asyncpg mocked)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.modules.integrations.providers.database_provider import (
    DatabaseProvider,
    _build_read_query,
)


class _FakeConn:
    def __init__(self, *, rows: list[Any] | None = None) -> None:
        self._rows = rows or []
        self.closed = False
        self.fetchval = AsyncMock(side_effect=self._fetchval)
        self.fetch = AsyncMock(return_value=self._rows)

    async def _fetchval(self, sql: str, *args: Any) -> Any:  # noqa: ARG002
        if "default_transaction_read_only" in sql:
            return "on"
        return 1

    @asynccontextmanager
    async def transaction(self, *, readonly: bool = False):  # noqa: ARG002
        yield

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_database_test_connection_success() -> None:
    conn = _FakeConn()

    async def connect(**kwargs: Any) -> _FakeConn:
        assert kwargs["server_settings"]["default_transaction_read_only"] == "on"
        assert kwargs["password"] == "secret"
        return conn

    provider = DatabaseProvider(connect=connect)
    result = await provider.test_connection(
        configuration={
            "host": "db.example.com",
            "port": 5432,
            "database": "addresses",
            "username": "ro",
            "schema": "public",
            "read_only": True,
        },
        secrets={"password": "secret"},
    )
    assert result.success is True
    assert result.authentication == "DB credentials"
    assert "SELECT only" in (result.permission or "")
    assert conn.closed is True


@pytest.mark.asyncio
async def test_database_missing_password() -> None:
    provider = DatabaseProvider()
    result = await provider.test_connection(
        configuration={
            "host": "db.example.com",
            "database": "addresses",
            "username": "ro",
        },
        secrets={},
    )
    assert result.success is False
    assert "senha" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_database_sync_table() -> None:
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    conn = _FakeConn(rows=rows)

    async def connect(**_kwargs: Any) -> _FakeConn:
        return conn

    provider = DatabaseProvider(connect=connect)
    result = await provider.sync(
        configuration={
            "host": "db.example.com",
            "database": "addresses",
            "username": "ro",
            "schema": "public",
            "table": "addresses",
            "row_limit": 100,
            "read_only": True,
        },
        secrets={"password": "x"},
    )
    assert result.success is True
    assert result.records_processed == 3
    sql = conn.fetch.await_args.args[0]
    assert '"public"."addresses"' in sql
    assert "LIMIT" in sql.upper()


@pytest.mark.asyncio
async def test_database_rejects_write_query() -> None:
    provider = DatabaseProvider()
    result = await provider.sync(
        configuration={
            "host": "db.example.com",
            "database": "addresses",
            "username": "ro",
            "query": "DELETE FROM addresses",
            "read_only": True,
        },
        secrets={"password": "x"},
    )
    assert result.success is False
    assert "SELECT" in result.message or "não permitida" in result.message.lower()


def test_build_read_query_custom_select() -> None:
    sql, args = _build_read_query(
        {"query": "SELECT id FROM public.addresses WHERE active", "row_limit": 10}
    )
    assert "SELECT id FROM public.addresses" in sql
    assert args == [10]


def test_build_read_query_rejects_multi_statement() -> None:
    with pytest.raises(Exception, match="múltiplos"):
        _build_read_query({"query": "SELECT 1; DROP TABLE addresses"})
