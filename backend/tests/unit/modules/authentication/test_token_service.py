"""Unit tests for JwtTokenService."""

from __future__ import annotations

from uuid import uuid4

import jwt
import pytest

from src.config.settings import Settings
from src.modules.authentication.services.jwt_token_service import JwtTokenService
from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims
from src.shared.infrastructure.exceptions import UnauthorizedError


@pytest.fixture
def token_service() -> JwtTokenService:
    return JwtTokenService(
        Settings(
            jwt_secret_key="test-secret-key-for-unit-tests-32b",
            jwt_access_token_expire_minutes=15,
        )
    )


def test_create_and_decode_access_token(token_service: JwtTokenService) -> None:
    user_id = uuid4()
    session_id = uuid4()
    claims = AccessTokenClaims(
        user_id=user_id,
        tenant_id=uuid4(),
        tenant_slug="universe",
        credentials_version=3,
        sid=session_id,
    )
    token = token_service.create_access_token(claims)
    decoded = token_service.decode_access_token(token)

    assert decoded.user_id == user_id
    assert decoded.tenant_slug == "universe"
    assert decoded.credentials_version == 3
    assert decoded.sid == session_id
    assert token_service.access_token_expires_in_seconds() == 15 * 60


def test_access_token_carries_no_profile_or_role_claims(
    token_service: JwtTokenService,
) -> None:
    claims = AccessTokenClaims(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="universe",
    )
    payload = jwt.decode(
        token_service.create_access_token(claims),
        options={"verify_signature": False},
    )

    for leaked in ("email", "full_name", "role_ids", "permissions"):
        assert leaked not in payload


def test_decode_rejects_non_access_token_use(token_service: JwtTokenService) -> None:
    claims = AccessTokenClaims(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="universe",
        token_use="mfa",
    )
    token = token_service.create_access_token(claims)

    with pytest.raises(UnauthorizedError):
        token_service.decode_access_token(token)


def test_decode_invalid_token_raises(token_service: JwtTokenService) -> None:
    with pytest.raises(UnauthorizedError):
        token_service.decode_access_token("not.a.jwt")
