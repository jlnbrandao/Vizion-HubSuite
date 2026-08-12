"""MFA: TOTP, recovery codes, WebAuthn helpers."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pyotp
from sqlalchemy import select

from src.config.settings import Settings
from src.modules.iam.models import MfaRecoveryCodeModel, UserMfaMethodModel
from src.modules.iam.utils import generate_token, sha256_hex
from src.shared.infrastructure.exceptions import UnauthorizedError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class MfaService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_mfa_token(self, *, user_id: UUID, tenant_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "purpose": "mfa",
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=self._settings.mfa_token_expire_minutes)).timestamp()
            ),
        }
        return jwt.encode(payload, self._settings.jwt_secret_key, algorithm="HS256")

    def decode_mfa_token(self, token: str) -> tuple[UUID, UUID]:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "purpose"]},
            )
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError("Invalid MFA token") from exc
        if payload.get("purpose") != "mfa":
            raise UnauthorizedError("Invalid MFA token")
        return UUID(str(payload["sub"])), UUID(str(payload["tenant_id"]))

    async def start_totp_enroll(self, user_id: UUID, email: str) -> dict[str, str]:
        secret = pyotp.random_base32()
        db = get_current_session()
        method = UserMfaMethodModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            user_id=user_id,
            method_type="totp",
            name="Authenticator",
            secret_encrypted=secret,
            confirmed_at=None,
        )
        db.add(method)
        await db.flush()
        uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=self._settings.app_name)
        return {"method_id": str(method.id), "secret": secret, "otpauth_uri": uri}

    async def confirm_totp(self, *, user_id: UUID, method_id: UUID, code: str) -> list[str]:
        db = get_current_session()
        method = await db.get(UserMfaMethodModel, method_id)
        if (
            method is None
            or method.user_id != user_id
            or method.method_type != "totp"
            or not method.secret_encrypted
        ):
            raise ValidationError("MFA method not found")
        if not pyotp.TOTP(method.secret_encrypted).verify(code, valid_window=1):
            raise UnauthorizedError("Invalid MFA code")
        method.confirmed_at = datetime.now(UTC)
        codes = await self._replace_recovery_codes(user_id)
        await db.flush()
        return codes

    async def has_confirmed_mfa(self, user_id: UUID) -> bool:
        db = get_current_session()
        result = await db.execute(
            select(UserMfaMethodModel).where(
                UserMfaMethodModel.user_id == user_id,
                UserMfaMethodModel.tenant_id == require_current_tenant_id(),
                UserMfaMethodModel.confirmed_at.is_not(None),
            )
        )
        return result.scalars().first() is not None

    async def verify_totp_or_recovery(self, *, user_id: UUID, code: str) -> str:
        db = get_current_session()
        result = await db.execute(
            select(UserMfaMethodModel).where(
                UserMfaMethodModel.user_id == user_id,
                UserMfaMethodModel.method_type == "totp",
                UserMfaMethodModel.confirmed_at.is_not(None),
            )
        )
        for method in result.scalars().all():
            if method.secret_encrypted and pyotp.TOTP(method.secret_encrypted).verify(
                code, valid_window=1
            ):
                return "otp"
        code_hash = sha256_hex(code.strip().lower())
        recovery = await db.execute(
            select(MfaRecoveryCodeModel).where(
                MfaRecoveryCodeModel.user_id == user_id,
                MfaRecoveryCodeModel.code_hash == code_hash,
                MfaRecoveryCodeModel.used_at.is_(None),
            )
        )
        row = recovery.scalar_one_or_none()
        if row is None:
            raise UnauthorizedError("Invalid MFA code")
        row.used_at = datetime.now(UTC)
        await db.flush()
        return "rck"

    async def _replace_recovery_codes(self, user_id: UUID) -> list[str]:
        db = get_current_session()
        existing = await db.execute(
            select(MfaRecoveryCodeModel).where(MfaRecoveryCodeModel.user_id == user_id)
        )
        for row in existing.scalars().all():
            await db.delete(row)
        plain_codes: list[str] = []
        for _ in range(10):
            raw = secrets.token_hex(4)
            plain_codes.append(raw)
            db.add(
                MfaRecoveryCodeModel(
                    id=uuid4(),
                    tenant_id=require_current_tenant_id(),
                    user_id=user_id,
                    code_hash=sha256_hex(raw),
                )
            )
        return plain_codes

    async def begin_webauthn_registration(self, user_id: UUID, username: str) -> dict[str, object]:
        """Return a simplified WebAuthn registration options payload."""
        challenge = generate_token(32)
        db = get_current_session()
        method = UserMfaMethodModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            user_id=user_id,
            method_type="webauthn",
            name="Passkey",
            credential_public=json.dumps({"challenge": challenge, "username": username}),
            confirmed_at=None,
        )
        db.add(method)
        await db.flush()
        return {
            "method_id": str(method.id),
            "challenge": challenge,
            "rp": {"name": self._settings.app_name, "id": "localhost"},
            "user": {"id": str(user_id), "name": username, "displayName": username},
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        }

    async def complete_webauthn_registration(
        self, *, user_id: UUID, method_id: UUID, credential_id: str, public_key: str
    ) -> None:
        db = get_current_session()
        method = await db.get(UserMfaMethodModel, method_id)
        if method is None or method.user_id != user_id or method.method_type != "webauthn":
            raise ValidationError("WebAuthn method not found")
        method.webauthn_credential_id = credential_id
        method.credential_public = public_key
        method.confirmed_at = datetime.now(UTC)
        await db.flush()

    async def begin_webauthn_authentication(self, user_id: UUID) -> dict[str, object]:
        db = get_current_session()
        result = await db.execute(
            select(UserMfaMethodModel).where(
                UserMfaMethodModel.user_id == user_id,
                UserMfaMethodModel.method_type == "webauthn",
                UserMfaMethodModel.confirmed_at.is_not(None),
            )
        )
        methods = list(result.scalars().all())
        if not methods:
            raise ValidationError("No WebAuthn credentials enrolled")
        challenge = generate_token(32)
        return {
            "challenge": challenge,
            "allowCredentials": [
                {"type": "public-key", "id": m.webauthn_credential_id}
                for m in methods
                if m.webauthn_credential_id
            ],
        }

    async def complete_webauthn_authentication(
        self, *, user_id: UUID, credential_id: str
    ) -> str:
        db = get_current_session()
        result = await db.execute(
            select(UserMfaMethodModel).where(
                UserMfaMethodModel.user_id == user_id,
                UserMfaMethodModel.webauthn_credential_id == credential_id,
                UserMfaMethodModel.confirmed_at.is_not(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise UnauthorizedError("Invalid WebAuthn assertion")
        return "pop"
