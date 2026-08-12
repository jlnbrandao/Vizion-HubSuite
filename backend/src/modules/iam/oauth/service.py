"""OIDC/OAuth2 Authorization Server helpers and client admin."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from src.config.settings import Settings
from src.modules.iam.models import (
    OAuthAuthorizationCodeModel,
    OAuthClientModel,
    OAuthConsentModel,
    OAuthScopeModel,
)
from src.modules.iam.utils import generate_token, sha256_hex
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.infrastructure.exceptions import (
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import (
    get_current_tenant_slug,
    require_current_tenant_id,
)

_DEFAULT_SCOPES = (
    ("openid", "OpenID", []),
    ("profile", "Profile", []),
    ("email", "Email", []),
    ("offline_access", "Offline access", []),
)


class OidcKeyStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._private_pem: bytes
        self._public_pem: bytes
        self._kid = "lanstar-1"
        if settings.oidc_jwt_private_key_pem.strip() and settings.oidc_jwt_public_key_pem.strip():
            self._private_pem = settings.oidc_jwt_private_key_pem.encode()
            self._public_pem = settings.oidc_jwt_public_key_pem.encode()
        else:
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self._private_pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            self._public_pem = key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

    @property
    def kid(self) -> str:
        return self._kid

    def sign(self, payload: dict[str, Any]) -> str:
        return jwt.encode(
            payload,
            self._private_pem,
            algorithm="RS256",
            headers={"kid": self._kid},
        )

    def jwks(self) -> dict[str, Any]:
        public = serialization.load_pem_public_key(self._public_pem)
        return {"keys": [json_jwk(public, self._kid)]}


def json_jwk(public_key: Any, kid: str) -> dict[str, Any]:
    numbers = public_key.public_numbers()

    def _b64(val: int) -> str:
        length = (val.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(val.to_bytes(length, "big")).rstrip(b"=").decode()

    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _b64(numbers.n),
        "e": _b64(numbers.e),
    }


class OAuthService:
    def __init__(
        self,
        settings: Settings,
        keys: OidcKeyStore,
        password_hasher: PasswordHasher,
    ) -> None:
        self._settings = settings
        self._keys = keys
        self._hasher = password_hasher

    def issuer(self) -> str:
        slug = get_current_tenant_slug() or "unknown"
        base = self._settings.tenant_base_domains[0] if self._settings.tenant_base_domains else "localhost"
        return self._settings.oidc_issuer_template.format(
            tenant_slug=slug, base_domain=base
        )

    async def ensure_default_scopes(self) -> None:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        for name, description, codes in _DEFAULT_SCOPES:
            existing = await db.execute(
                select(OAuthScopeModel).where(
                    OAuthScopeModel.tenant_id == tenant_id,
                    OAuthScopeModel.name == name,
                )
            )
            if existing.scalar_one_or_none() is None:
                db.add(
                    OAuthScopeModel(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        name=name,
                        description=description,
                        permission_codes=list(codes),
                    )
                )
        await db.flush()

    async def create_client(
        self,
        *,
        name: str,
        redirect_uris: list[str],
        grant_types: list[str] | None = None,
        is_confidential: bool = True,
        service_account_id: UUID | None = None,
    ) -> tuple[OAuthClientModel, str | None]:
        client_id = secrets.token_urlsafe(16)
        raw_secret: str | None = None
        secret_hash: str | None = None
        if is_confidential:
            raw_secret = secrets.token_urlsafe(32)
            secret_hash = self._hasher.hash(
                PlainPassword.from_login_attempt(raw_secret)
            ).value
        model = OAuthClientModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            client_id=client_id,
            client_secret_hash=secret_hash,
            name=name,
            redirect_uris=redirect_uris,
            grant_types=grant_types
            or ["authorization_code", "refresh_token", "client_credentials"],
            is_confidential=is_confidential,
            service_account_id=service_account_id,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return model, raw_secret

    async def list_clients(self) -> list[OAuthClientModel]:
        db = get_current_session()
        result = await db.execute(
            select(OAuthClientModel).where(
                OAuthClientModel.tenant_id == require_current_tenant_id()
            )
        )
        return list(result.scalars().all())

    async def get_client(self, client_id: str) -> OAuthClientModel:
        db = get_current_session()
        result = await db.execute(
            select(OAuthClientModel).where(
                OAuthClientModel.client_id == client_id,
                OAuthClientModel.tenant_id == require_current_tenant_id(),
            )
        )
        client = result.scalar_one_or_none()
        if client is None or not client.is_active:
            raise NotFoundError("OAuth client not found")
        return client

    async def delete_client(self, client_id: str) -> None:
        client = await self.get_client(client_id)
        await get_current_session().delete(client)

    async def create_authorization_code(
        self,
        *,
        client_id: str,
        user_id: UUID,
        redirect_uri: str,
        scopes: list[str],
        code_challenge: str | None,
        code_challenge_method: str | None,
    ) -> str:
        client = await self.get_client(client_id)
        if redirect_uri not in client.redirect_uris:
            raise ValidationError("Invalid redirect_uri")
        raw = generate_token()
        db = get_current_session()
        db.add(
            OAuthAuthorizationCodeModel(
                id=uuid4(),
                tenant_id=require_current_tenant_id(),
                code_hash=sha256_hex(raw),
                client_id=client_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                scopes=scopes,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        await db.flush()
        return raw

    async def grant_consent(
        self, *, user_id: UUID, client_id: str, scopes: list[str]
    ) -> OAuthConsentModel:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        result = await db.execute(
            select(OAuthConsentModel).where(
                OAuthConsentModel.tenant_id == tenant_id,
                OAuthConsentModel.user_id == user_id,
                OAuthConsentModel.client_id == client_id,
            )
        )
        consent = result.scalar_one_or_none()
        if consent is None:
            consent = OAuthConsentModel(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                client_id=client_id,
                scopes=scopes,
            )
            db.add(consent)
        else:
            consent.scopes = sorted(set(consent.scopes) | set(scopes))
            consent.granted_at = datetime.now(UTC)
        await db.flush()
        return consent

    def _verify_pkce(self, code_verifier: str, challenge: str, method: str | None) -> bool:
        method = (method or "S256").upper()
        if method == "PLAIN":
            return secrets.compare_digest(code_verifier, challenge)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return secrets.compare_digest(computed, challenge)

    async def exchange_code(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
        code_verifier: str | None,
    ) -> dict[str, Any]:
        client = await self.get_client(client_id)
        if client.is_confidential:
            if not client_secret or not client.client_secret_hash:
                raise UnauthorizedError("Invalid client")
            if not self._hasher.verify(
                PlainPassword.from_login_attempt(client_secret),
                HashedPassword.from_primitive(client.client_secret_hash),
            ):
                raise UnauthorizedError("Invalid client")
        db = get_current_session()
        result = await db.execute(
            select(OAuthAuthorizationCodeModel).where(
                OAuthAuthorizationCodeModel.code_hash == sha256_hex(code),
                OAuthAuthorizationCodeModel.tenant_id == require_current_tenant_id(),
            )
        )
        row = result.scalar_one_or_none()
        if row is None or row.consumed_at is not None:
            raise UnauthorizedError("Invalid code")
        if row.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Code expired")
        if row.client_id != client_id or row.redirect_uri != redirect_uri:
            raise UnauthorizedError("Invalid code")
        if row.code_challenge:
            if not code_verifier or not self._verify_pkce(
                code_verifier, row.code_challenge, row.code_challenge_method
            ):
                raise UnauthorizedError("PKCE verification failed")
        row.consumed_at = datetime.now(UTC)
        await db.flush()
        return self._issue_tokens(
            user_id=row.user_id,
            client_id=client_id,
            scopes=row.scopes,
        )

    async def client_credentials(
        self, *, client_id: str, client_secret: str, scopes: list[str]
    ) -> dict[str, Any]:
        client = await self.get_client(client_id)
        if not client.is_confidential or not client.client_secret_hash:
            raise UnauthorizedError("Invalid client")
        if not self._hasher.verify(
            PlainPassword.from_login_attempt(client_secret),
            HashedPassword.from_primitive(client.client_secret_hash),
        ):
            raise UnauthorizedError("Invalid client")
        if "client_credentials" not in client.grant_types:
            raise ForbiddenError("Grant not allowed")
        now = datetime.now(UTC)
        access = self._keys.sign(
            {
                "iss": self.issuer(),
                "sub": str(client.service_account_id or client.id),
                "aud": client_id,
                "client_id": client_id,
                "scope": " ".join(scopes),
                "token_use": "access",
                "tenant_id": str(require_current_tenant_id()),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            }
        )
        return {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(scopes),
        }

    def _issue_tokens(
        self, *, user_id: UUID, client_id: str, scopes: list[str]
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        access = self._keys.sign(
            {
                "iss": self.issuer(),
                "sub": str(user_id),
                "aud": client_id,
                "client_id": client_id,
                "scope": " ".join(scopes),
                "token_use": "access",
                "tenant_id": str(require_current_tenant_id()),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            }
        )
        result: dict[str, Any] = {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(scopes),
        }
        if "openid" in scopes:
            result["id_token"] = self._keys.sign(
                {
                    "iss": self.issuer(),
                    "sub": str(user_id),
                    "aud": client_id,
                    "iat": int(now.timestamp()),
                    "exp": int((now + timedelta(hours=1)).timestamp()),
                }
            )
        if "offline_access" in scopes:
            result["refresh_token"] = generate_token()
        return result

    def discovery_document(self) -> dict[str, Any]:
        issuer = self.issuer()
        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/oauth/authorize",
            "token_endpoint": f"{issuer}/oauth/token",
            "userinfo_endpoint": f"{issuer}/oauth/userinfo",
            "jwks_uri": f"{issuer}/jwks.json",
            "revocation_endpoint": f"{issuer}/oauth/revoke",
            "introspection_endpoint": f"{issuer}/oauth/introspect",
            "response_types_supported": ["code"],
            "grant_types_supported": [
                "authorization_code",
                "refresh_token",
                "client_credentials",
            ],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            "code_challenge_methods_supported": ["S256", "plain"],
            "scopes_supported": [name for name, _, _ in _DEFAULT_SCOPES],
        }
