import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.settings import settings
from ..shared.domain.exceptions import AlreadyExistsError, NotFoundError
from ..shared.infra.mail import SmtpMailSender
from ..shared.utils.time import current_datetime, get_expiration_time, get_expiration_timestamp
from .constants import INVITATION_EXPIRE_IN_DAYS, INVITATION_SUBJECT, INVITATION_TEXT
from .domain.entities import User
from .domain.exceptions import InvitationExpiredError, UnauthorizedError
from .domain.repos import InvitationRepository, UserRepository
from .domain.services import create_customer, create_support, invite_customer, invite_support
from .domain.vo import UserRole
from .schemas import Tokens, UserCreateForm
from .security import create_access_token, create_refresh_token, hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
            self,
            session: AsyncSession,
            user_repo: UserRepository,
            invitation_repo: InvitationRepository,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo

    async def register(self, token: str, form_data: UserCreateForm) -> Tokens:
        """Регистрация нового пользователя по приглашению"""

        # 1. Проверка приглашения на валидность
        invitation = await self.invitation_repo.get_by_token(token)
        if invitation is None:
            raise NotFoundError("Invitation not found")
        if not invitation.is_valid:
            raise InvitationExpiredError("Invitation expired or already used")

        # 2. Проверка существования пользователя (чтобы не было дубликата)
        existing_user = await self.user_repo.get_by_email(invitation.email)
        if existing_user is not None:
            raise AlreadyExistsError(f"User with email - '{invitation.email}' already exists'")

        # 3. Создание пользователя с определённым набором ролей и атрибутов
        if invitation.assigned_role.is_customer():
            user = create_customer(
                email=invitation.email,
                password_hash=hash_password(form_data.password),
                counterparty_id=invitation.counterparty_id,
                user_role=invitation.assigned_role,
                username=form_data.username,
                full_name=form_data.full_name,
            )
        elif invitation.assigned_role.is_support():
            user = create_support(
                email=invitation.email,
                password_hash=hash_password(form_data.password),
                user_role=invitation.assigned_role,
                username=form_data.username,
                full_name=form_data.full_name,
            )
        else:
            raise ValueError(
                f"Invite registration is not supported for the role - {invitation.assigned_role}"
            )

        # 4. Сохранение пользователя + пометка приглашения как использованное
        await self.user_repo.create(user)
        invitation.mark_as_used()
        await self.invitation_repo.upsert(invitation)

        # 5. Выпуск пары токенов
        tokens = await self.create_tokens_for_user(user)
        await self.session.commit()
        return tokens

    async def authenticate(self, email: str, password: str) -> Tokens:
        """Аутентификация пользователя по его учётным данным"""

        # 1. Проверка учётных данных пользователя
        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise UnauthorizedError(f"User not found by email - '{email}'")
        if not verify_password(password, user.password_hash.get_secret_value()) and \
                not user.is_active:
            raise UnauthorizedError("Invalid password or user is not active")

        # 2. Выпуск пары токенов
        tokens = await self.create_tokens_for_user(user)
        await self.session.commit()
        return tokens

    async def refresh_tokens(self, refresh_token: str) -> Tokens:
        """Обновление пары токенов с ротацией"""

        # 1. Проверка правил существования созданного токена
        stored_token = await self.user_repo.get_token_data(refresh_token)
        if stored_token is None:
            raise UnauthorizedError("Refresh token not found")
        if stored_token.revoked or stored_token.expires_at >= current_datetime():
            raise UnauthorizedError("Refresh token is already revoked or expired")

        # 2. Получение и валидация пользователя
        user = await self.user_repo.read(stored_token.user_id)
        if user is None or not user.is_active:
            await self.user_repo.revoke_token(stored_token.token)
            raise UnauthorizedError("User is not active")

        # 3. Ротация и выпуск новых токенов
        await self.user_repo.revoke_token(stored_token.token)
        new_tokens = await self.create_tokens_for_user(user)
        await self.session.commit()
        return new_tokens

    async def create_tokens_for_user(self, user: User) -> Tokens:
        """Выпуск пары токенов и сохранение для возможности ротации"""

        # 1. Выпуск токенов
        access_token = create_access_token(
            user_id=user.id,
            user_role=user.role,
            email=user.email,
            counterparty_id=user.counterparty_id,
        )
        refresh_token = create_refresh_token(user_id=user.id)

        # 2. Расчёт времени истечения токенов
        access_token_expires_at = get_expiration_timestamp(
            expires_in=timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
        )
        refresh_token_expires_at = get_expiration_time(
            expires_in=timedelta(days=settings.jwt.refresh_token_expires_in_days)
        )

        # 3. Сохранение refresh токена
        await self.user_repo.store_token(
            user_id=user.id, token=refresh_token, expires_at=refresh_token_expires_at,
        )

        return Tokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_token_expires_at,
        )


class InvitationService:
    def __init__(
            self,
            session: AsyncSession,
            repository: InvitationRepository,
            mail_sender: SmtpMailSender
    ) -> None:
        self.session = session
        self.repository = repository
        self.mail_sender = mail_sender

    async def send_invitation(
            self,
            invited_by: UUID,
            email: str,
            assigned_role: UserRole,
            counterparty_id: UUID | None = None,
    ):
        """Отправка приглашения на почту"""

        # 1. Поиск уже существующего приглашения
        invitation = await self.repository.get_active_by_email_and_role(email, assigned_role)

        # 2. Создание нового приглашения, если не нашлось существующее
        if invitation is None:
            logger.info("Invitation is not found, start creating new")

            if assigned_role.is_support():
                invitation = invite_support(
                    invited_by=invited_by, email=email, assigned_role=assigned_role
                )
            elif assigned_role.is_customer() and counterparty_id is not None:
                invitation = invite_customer(
                    invited_by=invited_by,
                    email=email,
                    counterparty_id=counterparty_id,
                    assigned_role=assigned_role,
                )
            else:
                raise ValueError("Invalid invite params")

            await self.repository.create(invitation)
            await self.session.commit()
            logger.info("Invitation saved successfully")

        # 3. Формирование письма и отправка
        invite_url = f"{settings.frontend_url}/auth/invite/accept?token={invitation.token}"
        context = {
            "email": email,
            "role": assigned_role.value.replace("_", " ").title(),
            "invite_url": invite_url,
            "expires_in_days": INVITATION_EXPIRE_IN_DAYS,
            "invited_by": f"{invited_by}",
            "app_name": settings.app.name,
            "support_email": settings.mail.support_email,
        }
        await self.mail_sender.send(
            to=invitation.email,
            subject=INVITATION_SUBJECT,
            plain_text=INVITATION_TEXT,
            template_name="email/invitation.html",
            context=context,
        )
        logger.info("Invitation sent: %s -> %s (%s)", invited_by, email, assigned_role)

        return invitation

    async def revoke_invitation(self, invitation_id: UUID) -> None:
        """Отзыв ещё не принятого приглашения (если было отправлено по ошибке)"""

        invitation = await self.repository.read(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation not found")

        await self.repository.delete(invitation_id)
        logger.info("Invitation deleted successfully")
