"""Unit tests for JoseTokenService."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.config.settings import Settings
from src.modules.authentication.services.jose_token_service import JoseTokenService
from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims
from src.shared.infrastructure.exceptions import UnauthorizedError


@pytest.fixture
def token_service() -> JoseTokenService:
    return JoseTokenService(
        Settings(
            jwt_secret_key="test-secret-key-for-unit-tests",
            jwt_access_token_expire_minutes=15,
        )
    )


def test_create_and_decode_access_token(token_service: JoseTokenService) -> None:
    user_id = uuid4()
    role_id = uuid4()
    claims = AccessTokenClaims(
        user_id=user_id,
        email="a@b.com",
        full_name="Ada",
        tenant_id=uuid4(),
        tenant_slug="universe",
        role_ids=(role_id,),
    )
    token = token_service.create_access_token(claims)
    decoded = token_service.decode_access_token(token)

    assert decoded.user_id == user_id
    assert decoded.email == "a@b.com"
    assert decoded.tenant_slug == "universe"
    assert decoded.role_ids == (role_id,)
    assert token_service.access_token_expires_in_seconds() == 15 * 60


def test_decode_invalid_token_raises(token_service: JoseTokenService) -> None:
    with pytest.raises(UnauthorizedError):
        token_service.decode_access_token("not.a.jwt")
