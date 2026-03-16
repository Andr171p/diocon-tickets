import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.entities import Invitation, UserRole
from ..core.errors import EmailSendingFailedError
from ..db.repos import InvitationRepository
from ..settings import INVITATION_EXPIRES_IN_DAYS, settings
from ..utils.commons import current_datetime
from ..utils.mail import send_mail

INVITATION_TEXT = (
    "Здравствуйте!\n\n"
    "Вас пригласили присоединиться к системе тикетов в роли {role}.\n"
    "Перейдите по ссылке для завершения регистрации:\n{invite_url}\n\n"
    "Ссылка действительна {expires_in_days} дней.\n\n"
    "С уважением,\nКоманда {app_name}"
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invitation_repo = InvitationRepository(session)

    async def send_invitation(
            self,
            invited_by: UUID,
            email: str,
            intended_role: UserRole,
            counterparty_id: UUID | None = None
    ) -> Invitation:
        invitation = await self.invitation_repo.find_active_by_email_and_role(email, intended_role)
        if invitation is None:
            invitation = Invitation(
                email=email,
                created_by=invited_by,
                intended_role=intended_role,
                counterparty_id=counterparty_id,
                expires_at=current_datetime() + timedelta(days=INVITATION_EXPIRES_IN_DAYS),
            )
        invite_url = f"{settings.frontend_url}/auth/invite/accept?token={invitation.token}"
        context = {
            "email": email,
            "role": intended_role.value.replace("_", " ").title(),
            "invite_url": invite_url,
            "expires_in_days": INVITATION_EXPIRES_IN_DAYS,
            "invited_by": f"{invited_by}",
            "app_name": settings.app.name,
            "support_email": settings.mail.support_email,
        }
        try:
            await self.invitation_repo.create(invitation)
            await send_mail(
                to=invitation.email,
                subject="Приглашение в систему тикетов",
                plain_text=INVITATION_TEXT.format(**context),
                template_name="email/invitation.html",
                context=context,
            )
            await self.session.commit()
        except EmailSendingFailedError:
            logger.exception("Email sending failed")
            await self.session.rollback()
        logger.info("Invitation sent: %s -> %s (%s)", invited_by, email, intended_role)
        return invitation
