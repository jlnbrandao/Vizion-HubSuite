"""Access token claims IAM extensions."""

from __future__ import annotations

from uuid import uuid4

from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims


def test_claims_roundtrip_with_amr_sid() -> None:
    sid = uuid4()
    claims = AccessTokenClaims(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="universe",
        amr=("pwd", "otp"),
        acr="mfa",
        sid=sid,
    )
    restored = AccessTokenClaims.from_primitive(claims.to_primitive())
    assert restored.amr == ("pwd", "otp")
    assert restored.acr == "mfa"
    assert restored.sid == sid
