from typing import Annotated

from collections.abc import Iterable
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer

from src.core.redis import redis_client
from src.core.settings import settings
from src.shared.dependencies import PaginationDep, SessionDep
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.mail import SmtpMailSender
from src.shared.schemas import Page

from .domain.authz import Subject
from .domain.exceptions import PermissionDeniedError, UnauthorizedError
from .domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from .domain.vo import Email, UserRole
from .infra.blacklist import RedisTokenBlacklist
from .infra.repos import SqlInvitationRepository, SqlUserRepository
from .mappers import map_user_to_response
from .schemas import CurrentUser, UserResponse
from .security import validate_token
from .services import AuthService, InvitationService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


def get_user_repo(session: SessionDep) -> SqlUserRepository:
    return SqlUserRepository(session)


def get_token_blacklist() -> TokenBlacklist:
    return RedisTokenBlacklist(redis_client)


def get_invitation_repo(session: SessionDep) -> SqlInvitationRepository:
    return SqlInvitationRepository(session)


def get_auth_service(
        session: SessionDep,
        user_repo: Annotated[UserRepository, Depends(get_user_repo)],
        invitation_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
        blacklist: Annotated[TokenBlacklist, Depends(get_token_blacklist)],
) -> AuthService:
    return AuthService(
        session, user_repo=user_repo, invitation_repo=invitation_repo, blacklist=blacklist
    )


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


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]


async def get_current_subject(
        token: Annotated[str, Depends(oauth2_scheme)],
        blacklist: Annotated[TokenBlacklist, Depends(get_token_blacklist)],
) -> Subject:
    payload = validate_token(token)
    jti, sid, stype = payload.get("jti"), payload.get("sub"), payload.get("type")

    if jti is None or await blacklist.is_revoked(jti):
        raise UnauthorizedError("Token has been revoked or missing jti")

    if sid is None:
        raise UnauthorizedError("Invalid token: missing sub claim")

    return Subject(
        id=sid,
        type=stype,
        email=Email(payload["email"]) if "email" in payload else None,
        roles=payload.get("roles", []),
        counterparty_id=payload.get("counterparty_id"),
        scopes=payload.get("scopes", []),
    )


def get_current_user(current_subject: Subject = Depends(get_current_subject)) -> CurrentUser:
    if not current_subject.is_user:
        raise PermissionDeniedError("Not a user")

    return CurrentUser(
        id=current_subject.id,
        email=f"{current_subject.email}",
        roles=current_subject.roles,
        counterparty_id=current_subject.counterparty_id,
    )


CurrentSubjectDep = Annotated[Subject, Depends(get_current_subject)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def get_me_or_404(current_user: CurrentUserDep, user_repo: UserRepoDep) -> UserResponse:
    user = await user_repo.read(current_user.id)
    if user is None:
        raise NotFoundError(f"User with ID {current_user.id} not found")

    return map_user_to_response(user)


async def get_user_or_404(user_id: UUID, user_repo: UserRepoDep) -> UserResponse:
    user = await user_repo.read(user_id)
    if user is None:
        raise NotFoundError(f"User with ID {user_id} not found")

    return map_user_to_response(user)


async def get_users_page(
        pagination: PaginationDep,
        user_repo: UserRepoDep,
        role: Annotated[
            list[UserRole] | None, Query(..., description="Фильтр по ролям")
        ] = None,
) -> Page[UserResponse]:
    page = await user_repo.paginate(pagination, roles=role)
    return page.to_response(map_user_to_response)


ActiveUserDep = Annotated[UserResponse, Depends(get_me_or_404)]
UserByIdDep = Annotated[UserResponse, Depends(get_user_or_404)]
UsersPageDep = Annotated[Page[UserResponse], Depends(get_users_page)]


def require_role(allowed_roles: Iterable[UserRole]):

    def checker(current_subject: CurrentSubjectDep):
        return any(current_subject.has_role(allowed_role) for allowed_role in allowed_roles)

    return checker
