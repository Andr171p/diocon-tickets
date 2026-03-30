from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ..core.settings import settings
from ..shared.dependencies import SessionDep
from ..shared.infra.mail import SmtpMailSender
from .domain.exceptions import PermissionDeniedError, UnauthorizedError
from .domain.repos import InvitationRepository, UserRepository
from .domain.vo import UserRole
from .infra.repos import SqlInvitationRepository, SqlUserRepository
from .schemas import CurrentUser
from .security import validate_token
from .services import AuthService, InvitationService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


def get_user_repo(session: SessionDep) -> UserRepository:
    return SqlUserRepository(session)


def get_invitation_repo(session: SessionDep) -> InvitationRepository:
    return SqlInvitationRepository(session)


def get_auth_service(
        session: SessionDep,
        user_repo: Annotated[UserRepository, Depends(get_user_repo)],
        invitation_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
) -> AuthService:
    return AuthService(session, user_repo=user_repo, invitation_repo=invitation_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_mail_sender() -> SmtpMailSender:
    return SmtpMailSender(
        smtp_host=settings.mail.smtp_host,
        smtp_port=settings.mail.smtp_port,
        use_tls=settings.mail.smtp_use_tls,
    )


def get_invitation_service(
        session: SessionDep,
        repository: Annotated[InvitationRepository, Depends(get_invitation_repo)],
        mail_sender: Annotated[SmtpMailSender, Depends(get_mail_sender)],
) -> InvitationService:
    return InvitationService(session, repository=repository, mail_sender=mail_sender)


InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    """Получение текущего пользователя"""

    payload = validate_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token: missing sub claim")

    return CurrentUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        counterparty_id=payload.get("counterparty_id"),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_current_support_user(current_user: CurrentUserDep) -> CurrentUser:
    """Зависимость для эндпоинтов, доступных только сотрудникам поддержки"""

    if current_user.role not in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        raise PermissionDeniedError("Access restricted to support staff only")

    return current_user


CurrentSupportUserDep = Annotated[CurrentUserDep, Depends(get_current_support_user)]
