from typing import Annotated

from collections.abc import Iterable
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer

from src.core.redis import redis_client
from src.core.settings import settings
from src.shared.dependencies import EventPublisherDep, PaginationDep, SessionDep
from src.shared.domain.exceptions import NotFoundError
from src.shared.domain.repos import get_or_raise_404
from src.shared.infra.mail import SmtpMailSender
from src.shared.schemas import Page

from .domain.authz import Subject
from .domain.entities import Invitation
from .domain.exceptions import PermissionDeniedError, UnauthorizedError
from .domain.repos import InvitationRepository, TokenStore, UserFilters, UserRepository
from .domain.vo import Email, UserRole
from .infra.repos import SqlInvitationRepository, SqlUserRepository
from .infra.token_store import RedisTokenStore
from .mappers import map_invitation_to_response, map_user_to_response
from .schemas import CurrentUser, InvitationResponse, UserResponse
from .security import validate_token
from .services import AuthService, InvitationService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


def get_user_repo(session: SessionDep) -> SqlUserRepository:
    return SqlUserRepository(session)


def get_token_store() -> TokenStore:
    return RedisTokenStore(redis_client)


def get_invitation_repo(session: SessionDep) -> SqlInvitationRepository:
    return SqlInvitationRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
InvitationRepoDep = Annotated[InvitationRepository, Depends(get_invitation_repo)]


def get_auth_service(
        session: SessionDep,
        user_repo: UserRepoDep,
        invitation_repo: InvitationRepoDep,
        token_store: Annotated[TokenStore, Depends(get_token_store)],
) -> AuthService:
    return AuthService(
        uow=session,
        user_repo=user_repo,
        invitation_repo=invitation_repo,
        token_store=token_store,
    )


def get_mail_sender() -> SmtpMailSender:
    return SmtpMailSender(
        smtp_host=settings.mail.smtp_host,
        smtp_port=settings.mail.smtp_port,
        use_tls=settings.mail.smtp_use_tls,
    )


def get_invitation_service(
        session: SessionDep,
        invitation_repo: InvitationRepoDep,
        mail_sender: Annotated[SmtpMailSender, Depends(get_mail_sender)],
        event_publisher: EventPublisherDep,
) -> InvitationService:
    return InvitationService(
        uow=session,
        invitation_repo=invitation_repo,
        mail_sender=mail_sender,
        event_publisher=event_publisher,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]


async def get_current_subject(
        token: Annotated[str, Depends(oauth2_scheme)],
        blacklist: Annotated[TokenStore, Depends(get_token_store)],
) -> Subject:
    payload = validate_token(token)
    jti, sub, type_ = payload.get("jti"), payload.get("sub"), payload.get("sub_type")

    if jti is None or await blacklist.is_revoked(jti):
        raise UnauthorizedError("Token has been revoked or missing jti")

    if sub is None:
        raise UnauthorizedError("Invalid token: missing sub claim")

    return Subject(
        id=sub,
        type=type_,
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
        email=current_subject.email.value,
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


def get_user_filters(
        roles: list[UserRole] | None = Query(None, min_length=1, description="A least one filter"),
        counterparty_id: UUID | None = Query(None, description="Идентификатор контрагента"),
) -> UserFilters:
    return UserFilters(roles=roles, counterparty_id=counterparty_id)


async def paginate_users(
        pagination: PaginationDep,
        user_repo: UserRepoDep,
        filters: UserFilters = Depends(get_user_filters),
) -> Page[UserResponse]:
    page = await user_repo.paginate(pagination, filters=filters)
    return page.to_response(map_user_to_response)


def require_role(allowed_roles: Iterable[UserRole]):

    def checker(current_subject: CurrentSubjectDep):
        return current_subject.has_any_role(allowed_roles)

    return checker


async def get_invitation_or_404(
        invitation_id: UUID, invitation_repo: InvitationRepoDep
) -> InvitationResponse:
    invitation = await get_or_raise_404(invitation_repo.read, invitation_id, Invitation)
    return map_invitation_to_response(invitation)


async def paginate_invitations(
        pagination: PaginationDep, invitation_repo: InvitationRepoDep
) -> Page[InvitationResponse]:
    page = await invitation_repo.paginate(pagination)
    return page.to_response(map_invitation_to_response)
