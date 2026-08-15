"""Account lifecycle: invitations and password reset."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from src.config.settings import Settings
from src.modules.iam.email_sender import EmailSender
from src.modules.iam.models import PasswordResetTokenModel, UserInvitationModel
from src.modules.iam.policies.service import AuthPolicyService
from src.modules.iam.utils import generate_token, sha256_hex
from src.modules.users.commands.user_commands import (
    ChangeUserPasswordCommand,
    CreateUserCommand,
)
from src.modules.users.queries.user_queries import GetUserByEmailQuery
from src.modules.users.repositories.user_model import UserModel
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import NotFoundError, UnauthorizedError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class LifecycleService:
    def __init__(
        self,
        settings: Settings,
        email_sender: EmailSender,
        command_bus: CommandBus,
        query_bus: QueryBus,
        password_hasher: PasswordHasher,
        auth_policies: AuthPolicyService,
    ) -> None:
        self._settings = settings
        self._mail = email_sender
        self._commands = command_bus
        self._queries = query_bus
        self._hasher = password_hasher
        self._policies = auth_policies

    async def create_invitation(
        self,
        *,
        email: str,
        username: str,
        full_name: str,
        role_ids: list[UUID],
        invited_by: UUID | None,
    ) -> tuple[UserInvitationModel, str]:
        raw = generate_token()
        model = UserInvitationModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            email=email.strip().lower(),
            username=username.strip(),
            full_name=full_name.strip(),
            role_ids=role_ids,
            token_hash=sha256_hex(raw),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self._settings.invitation_expire_hours),
            invited_by=invited_by,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        self._mail.send(
            to=email,
            subject="You are invited to Lanstar",
            body=(
                f"Accept your invitation with token: {raw}\n"
                "Use POST /api/v1/auth/accept-invitation"
            ),
        )
        return model, raw

    async def accept_invitation(self, *, token: str, password: str) -> UUID:
        db = get_current_session()
        result = await db.execute(
            select(UserInvitationModel).where(
                UserInvitationModel.token_hash == sha256_hex(token),
                UserInvitationModel.tenant_id == require_current_tenant_id(),
            )
        )
        invitation = result.scalar_one_or_none()
        if invitation is None or invitation.accepted_at is not None:
            raise ValidationError("Invalid invitation")
        if invitation.expires_at < datetime.now(UTC):
            raise ValidationError("Invitation expired")
        user_id: UUID = await self._commands.execute(
            CreateUserCommand(
                tenant_id=invitation.tenant_id,
                email=invitation.email,
                username=invitation.username,
                full_name=invitation.full_name,
                password=password,
                role_ids=frozenset(invitation.role_ids),
            )
        )
        invitation.accepted_at = datetime.now(UTC)
        user_row = await db.get(UserModel, user_id)
        if user_row is not None:
            user_row.invitation_accepted_at = datetime.now(UTC)
            user_row.must_change_password = False
        await db.flush()
        return user_id

    async def forgot_password(self, *, email: str) -> None:
        tenant_id = require_current_tenant_id()
        try:
            user = await self._queries.ask(GetUserByEmailQuery(tenant_id=tenant_id, email=email))
        except NotFoundError:
            return
        raw = generate_token()
        db = get_current_session()
        db.add(
            PasswordResetTokenModel(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user.id,
                token_hash=sha256_hex(raw),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self._settings.password_reset_expire_hours),
            )
        )
        await db.flush()
        self._mail.send(
            to=email,
            subject="Reset your Lanstar password",
            body=f"Reset token: {raw}\nUse POST /api/v1/auth/reset-password",
        )

    async def reset_password(self, *, token: str, new_password: str) -> None:
        db = get_current_session()
        result = await db.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == sha256_hex(token),
                PasswordResetTokenModel.tenant_id == require_current_tenant_id(),
            )
        )
        row = result.scalar_one_or_none()
        if row is None or row.used_at is not None:
            raise UnauthorizedError("Invalid reset token")
        if row.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Reset token expired")
        policy = await self._policies.get_or_create()
        plain = PlainPassword.from_primitive(new_password)
        await self._policies.assert_password_not_reused(
            user_id=row.user_id,
            plain=plain,
            hasher=self._hasher,
            history_count=policy.password_history_count,
        )
        user_row = await db.get(UserModel, row.user_id)
        if user_row is not None:
            await self._policies.add_password_history(row.user_id, user_row.hashed_password)
        await self._commands.execute(
            ChangeUserPasswordCommand(user_id=row.user_id, new_password=new_password)
        )
        if user_row is not None:
            user_row.password_changed_at = datetime.now(UTC)
            user_row.must_change_password = False
        row.used_at = datetime.now(UTC)
        await db.flush()
