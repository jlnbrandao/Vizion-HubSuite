"""Authentication command handlers.

Cross-module:
  - GetUserByEmailQuery / GetUserByUsernameQuery (Users) via QueryBus
  - PasswordHasher (Users) via DI
Never imports Users domain entities.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta

from src.config.settings import Settings
from src.modules.authentication.commands.auth_commands import (
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
)
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto, TokenPairDto
from src.modules.authentication.events.auth_events import (
    TokenRefreshedEvent,
    UserLoggedInEvent,
    UserLoggedOutEvent,
)
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.services.token_service import TokenService
from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims
from src.modules.authentication.value_objects.refresh_token import RefreshToken
from src.modules.iam.mfa.service import MfaService
from src.modules.iam.policies.service import AuthPolicyService
from src.modules.iam.sessions.service import SessionService
from src.modules.users.dtos.user_dtos import UserAuthDto, UserDto
from src.modules.users.queries.user_queries import (
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByUsernameQuery,
)
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.event_bus import EventBus
from src.shared.application.handler import CommandHandler
from src.shared.application.query_bus import QueryBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import NotFoundError, UnauthorizedError, ValidationError
from src.shared.infrastructure.security.session_denylist import SessionDenylist
from src.shared.infrastructure.tenant_context import (
    get_current_tenant_slug,
    require_current_tenant_id,
)

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


class LoginHandler(CommandHandler[LoginCommand, TokenPairDto]):
    def __init__(
        self,
        query_bus: QueryBus,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        refresh_store: RefreshTokenStore,
        event_bus: EventBus,
        uow_factory: UowFactory,
        session_service: SessionService,
        mfa_service: MfaService,
        auth_policy_service: AuthPolicyService,
        settings: Settings,
    ) -> None:
        self._query_bus = query_bus
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._refresh_store = refresh_store
        self._event_bus = event_bus
        self._uow_factory = uow_factory
        self._sessions = session_service
        self._mfa = mfa_service
        self._policies = auth_policy_service
        self._settings = settings

    async def handle(self, command: LoginCommand) -> TokenPairDto:
        user = await self._load_user(command.login)
        async with self._uow_factory() as uow:
            policy = await self._policies.get_or_create()
            if not policy.password_login_enabled:
                raise UnauthorizedError("Password login disabled")
            await self._policies.assert_not_locked(user.id)
            try:
                self._assert_credentials(command.password, user)
            except UnauthorizedError:
                await self._policies.record_failed_login(user.id, policy)
                await uow.commit()
                raise
            await self._policies.clear_failed_login(user.id)

            needs_mfa = False
            if self._settings.iam_mfa_enabled:
                has_mfa = await self._mfa.has_confirmed_mfa(user.id)
                if policy.mfa_required == "required" or has_mfa:
                    needs_mfa = True
            if needs_mfa:
                await uow.commit()
                return TokenPairDto(
                    access_token="",
                    refresh_token="",
                    expires_in=0,
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    mfa_required=True,
                    mfa_token=self._mfa.issue_mfa_token(
                        user_id=user.id, tenant_id=require_current_tenant_id()
                    ),
                )

            pair = await self._issue_tokens(user, amr=("pwd",))
            await uow.commit()

        await self._event_bus.publish(
            UserLoggedInEvent(
                aggregate_id=user.id,
                user_id=user.id,
                email=user.email,
            )
        )
        return pair

    async def _load_user(self, login: str) -> UserAuthDto:
        identifier = login.strip()
        if not identifier:
            raise UnauthorizedError("Invalid credentials")

        tenant_id = require_current_tenant_id()
        try:
            if "@" in identifier:
                return await self._query_bus.ask(
                    GetUserByEmailQuery(tenant_id=tenant_id, email=identifier)
                )
            return await self._query_bus.ask(
                GetUserByUsernameQuery(tenant_id=tenant_id, username=identifier)
            )
        except (NotFoundError, ValidationError) as exc:
            raise UnauthorizedError("Invalid credentials") from exc

    def _assert_credentials(self, password: str, user: UserAuthDto) -> None:
        if not user.is_active:
            raise UnauthorizedError("Invalid credentials")
        try:
            plain = PlainPassword.from_login_attempt(password)
        except ValueError as exc:
            raise UnauthorizedError("Invalid credentials") from exc

        hashed = HashedPassword.from_primitive(user.hashed_password)
        if not self._password_hasher.verify(plain, hashed):
            raise UnauthorizedError("Invalid credentials")

    async def _issue_tokens(
        self, user: UserAuthDto, *, amr: tuple[str, ...]
    ) -> TokenPairDto:
        tenant_id = require_current_tenant_id()
        tenant_slug = get_current_tenant_slug() or ""
        if user.tenant_id != tenant_id:
            raise UnauthorizedError("Invalid credentials")

        expires_at = datetime.now(UTC) + timedelta(
            days=self._settings.jwt_refresh_token_expire_days
        )
        session_id = await self._sessions.create(
            user_id=user.id,
            amr=amr,
            expires_at=expires_at,
        )
        claims = AccessTokenClaims(
            user_id=user.id,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            credentials_version=user.credentials_version,
            amr=amr,
            acr="pwd",
            sid=session_id,
        )
        access = self._token_service.create_access_token(claims)
        refresh = RefreshToken.generate()
        session = RefreshSessionDto(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            role_ids=user.role_ids,
            created_at=datetime.now(UTC),
            session_id=session_id,
            amr=amr,
        )
        await self._refresh_store.save(refresh, session)
        return TokenPairDto(
            access_token=access,
            refresh_token=refresh.value,
            expires_in=self._token_service.access_token_expires_in_seconds(),
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
        )


class LogoutHandler(CommandHandler[LogoutCommand, None]):
    def __init__(
        self,
        refresh_store: RefreshTokenStore,
        event_bus: EventBus,
        uow_factory: UowFactory,
        session_service: SessionService,
        session_denylist: SessionDenylist,
    ) -> None:
        self._refresh_store = refresh_store
        self._event_bus = event_bus
        self._uow_factory = uow_factory
        self._sessions = session_service
        self._denylist = session_denylist

    async def handle(self, command: LogoutCommand) -> None:
        try:
            token = RefreshToken.from_primitive(command.refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        session = await self._refresh_store.get(token)
        await self._refresh_store.delete(token)

        if session is not None:
            if session.session_id is not None:
                async with self._uow_factory() as uow:
                    await self._sessions.revoke(session.session_id, session.user_id)
                    await uow.commit()
                # Access token must die with the session, not at its natural expiry.
                await self._denylist.revoke(session.session_id)
            await self._event_bus.publish(
                UserLoggedOutEvent(
                    aggregate_id=session.user_id,
                    user_id=session.user_id,
                    email=session.email,
                )
            )


class RefreshTokenHandler(CommandHandler[RefreshTokenCommand, TokenPairDto]):
    def __init__(
        self,
        token_service: TokenService,
        refresh_store: RefreshTokenStore,
        event_bus: EventBus,
        query_bus: QueryBus,
        uow_factory: UowFactory,
        session_service: SessionService,
        settings: Settings,
    ) -> None:
        self._token_service = token_service
        self._refresh_store = refresh_store
        self._event_bus = event_bus
        self._query_bus = query_bus
        self._uow_factory = uow_factory
        self._sessions = session_service
        self._settings = settings

    async def handle(self, command: RefreshTokenCommand) -> TokenPairDto:
        try:
            old_token = RefreshToken.from_primitive(command.refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        session = await self._refresh_store.get(old_token)
        if session is None:
            raise UnauthorizedError("Invalid or expired refresh token")

        host_tenant_id = require_current_tenant_id()
        if session.tenant_id != host_tenant_id:
            raise UnauthorizedError("Invalid or expired refresh token")

        try:
            user: UserDto = await self._query_bus.ask(
                GetUserByIdQuery(user_id=session.user_id)
            )
        except NotFoundError as exc:
            await self._refresh_store.delete(old_token)
            await self._refresh_store.delete_all_for_user(session.user_id)
            raise UnauthorizedError("Invalid or expired refresh token") from exc

        await self._refresh_store.delete(old_token)

        if not user.is_active:
            await self._refresh_store.delete_all_for_user(session.user_id)
            raise UnauthorizedError("Invalid or expired refresh token")

        async with self._uow_factory() as uow:
            expires_at = datetime.now(UTC) + timedelta(
                days=self._settings.jwt_refresh_token_expire_days
            )
            session_id = session.session_id or await self._sessions.create(
                user_id=user.id,
                amr=session.amr,
                expires_at=expires_at,
            )
            claims = AccessTokenClaims(
                user_id=user.id,
                tenant_id=session.tenant_id,
                tenant_slug=session.tenant_slug,
                credentials_version=user.credentials_version,
                amr=session.amr,
                sid=session_id,
            )
            access = self._token_service.create_access_token(claims)
            new_refresh = RefreshToken.generate()
            new_session = RefreshSessionDto(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                tenant_id=session.tenant_id,
                tenant_slug=session.tenant_slug,
                role_ids=user.role_ids,
                created_at=datetime.now(UTC),
                session_id=session_id,
                amr=session.amr,
            )
            await self._refresh_store.save(new_refresh, new_session)
            await uow.commit()

        await self._event_bus.publish(
            TokenRefreshedEvent(
                aggregate_id=user.id,
                user_id=user.id,
                email=user.email,
            )
        )

        return TokenPairDto(
            access_token=access,
            refresh_token=new_refresh.value,
            expires_in=self._token_service.access_token_expires_in_seconds(),
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
        )
