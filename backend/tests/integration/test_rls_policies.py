"""Row Level Security verified as the application role, not as the table owner.

The owner bypasses RLS unless the table is FORCEd, so these assertions connect as
`vizion_app` — the role the API actually uses. A missing policy here means one
mistake in a WHERE clause is enough to leak another tenant's data.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from src.config.settings import get_settings

#: Every tenant-scoped table the Hub owns. Adding a slice means adding it here.
TENANT_SCOPED_TABLES = (
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "permission_groups",
    "permission_group_items",
    "role_permission_groups",
    "audit_events",
    "auth_sessions",
    "user_mfa_methods",
    "api_keys",
    "service_accounts",
    "access_policies",
    "resource_acls",
    "tenant_services",
    "usage_records",
    "billing_customers",
    "billing_payment_methods",
    "billing_invoices",
    "billing_invoice_lines",
)

APP_ROLE = "vizion_app"


def _dsn(user: str, password: str) -> str:
    settings = get_settings()
    base = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    tail = base.split("@", 1)[1]
    return f"postgresql://{user}:{password}@{tail}"


@pytest_asyncio.fixture
async def owner_connection() -> Any:
    import asyncpg

    connection = await asyncpg.connect(
        _dsn(*_credentials_from_settings()), timeout=5
    )
    try:
        yield connection
    finally:
        await connection.close()


def _credentials_from_settings() -> tuple[str, str]:
    base = get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://")
    credentials = base.split("://", 1)[1].split("@", 1)[0]
    user, _, password = credentials.partition(":")
    return user, password


@pytest_asyncio.fixture
async def app_connection() -> Any:
    import asyncpg

    try:
        connection = await asyncpg.connect(_dsn(APP_ROLE, APP_ROLE), timeout=5)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Role {APP_ROLE} unavailable: {type(exc).__name__}")
    try:
        yield connection
    finally:
        await connection.close()


async def test_tenant_tables_force_row_level_security(owner_connection: Any) -> None:
    rows = await owner_connection.fetch(
        """
        SELECT relname, relrowsecurity, relforcerowsecurity
          FROM pg_class
         WHERE relname = ANY($1::text[])
        """,
        list(TENANT_SCOPED_TABLES),
    )
    found = {row["relname"]: row for row in rows}

    missing = [table for table in TENANT_SCOPED_TABLES if table not in found]
    assert not missing, f"tables absent from the database: {missing}"

    unprotected = [
        table
        for table, row in found.items()
        if not row["relrowsecurity"] or not row["relforcerowsecurity"]
    ]
    assert not unprotected, f"RLS not forced on: {unprotected}"


async def test_every_tenant_table_has_a_policy(owner_connection: Any) -> None:
    rows = await owner_connection.fetch(
        "SELECT tablename, count(*) AS policies FROM pg_policies"
        " WHERE tablename = ANY($1::text[]) GROUP BY tablename",
        list(TENANT_SCOPED_TABLES),
    )
    counts = {row["tablename"]: row["policies"] for row in rows}

    without_policy = [table for table in TENANT_SCOPED_TABLES if not counts.get(table)]
    assert not without_policy, f"no RLS policy on: {without_policy}"


async def test_app_role_sees_only_the_bound_tenant(
    owner_connection: Any, app_connection: Any
) -> None:
    tenants = await owner_connection.fetch("SELECT id FROM tenants ORDER BY slug")
    if len(tenants) < 2:
        pytest.skip("Needs at least two tenants — run python -m scripts.seed")
    first, second = tenants[0]["id"], tenants[1]["id"]

    await app_connection.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(first)
    )
    visible = await app_connection.fetch("SELECT DISTINCT tenant_id FROM users")

    assert visible, "the app role should see its own tenant's users"
    assert {row["tenant_id"] for row in visible} == {first}
    assert second not in {row["tenant_id"] for row in visible}


async def test_app_role_cannot_write_into_another_tenant(
    owner_connection: Any, app_connection: Any
) -> None:
    tenants = await owner_connection.fetch("SELECT id FROM tenants ORDER BY slug")
    if len(tenants) < 2:
        pytest.skip("Needs at least two tenants — run python -m scripts.seed")
    mine, theirs = tenants[0]["id"], tenants[1]["id"]

    await app_connection.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(mine)
    )

    with pytest.raises(Exception) as error:
        await app_connection.execute(
            "INSERT INTO usage_records"
            " (id, tenant_id, service, metric, granularity, period_start, quantity)"
            " VALUES ($1, $2, 'iam', 'itest', 'day', now(), 1)",
            uuid4(),
            theirs,
        )

    assert "policy" in str(error.value).lower() or "row-level" in str(error.value).lower()


async def test_app_role_sees_nothing_without_a_tenant_bound(app_connection: Any) -> None:
    await app_connection.execute("SELECT set_config('app.current_tenant_id', '', false)")

    assert await app_connection.fetchval("SELECT count(*) FROM users") == 0
    assert await app_connection.fetchval("SELECT count(*) FROM audit_events") == 0
