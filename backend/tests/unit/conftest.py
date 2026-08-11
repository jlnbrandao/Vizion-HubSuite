"""Shared unit-test fixtures for multi-tenant context."""

from __future__ import annotations

from uuid import UUID

import pytest

from src.shared.infrastructure.tenant_context import bind_tenant, unbind_tenant

UNIVERSE_TENANT_ID = UUID("a0000000-0000-4000-8000-000000000001")


@pytest.fixture
def tenant_id() -> UUID:
    return UNIVERSE_TENANT_ID


@pytest.fixture(autouse=True)
def bind_test_tenant() -> None:
    id_token, slug_token, name_token = bind_tenant(
        UNIVERSE_TENANT_ID, slug="universe", name="Universe"
    )
    yield
    unbind_tenant(id_token, slug_token, name_token)
