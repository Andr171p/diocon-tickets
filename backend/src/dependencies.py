from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from .core.entities import UserRole
from .core.errors import UnauthorizedError
from .db.base import session_factory
from .db.repos import AttachmentRepository, CounterpartyRepository
from .s3 import get_private_s3_client, get_public_s3_client
from .services import AttachmentService, AuthService, InvitationService, UserService
from .utils.secutiry import validate_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


async def get_db() -> AsyncSession:
    async with session_factory() as session:
        yield session


def get_counterparty_repo(session: AsyncSession = Depends(get_db)) -> CounterpartyRepository:
    return CounterpartyRepository(session)


def get_attachment_repo(session: AsyncSession = Depends(get_db)) -> AttachmentRepository:
    return AttachmentRepository(session)


def get_invitation_service(session: AsyncSession = Depends(get_db)) -> InvitationService:
    return InvitationService(session)


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)


def get_pubic_attachment_service(
        repository: AttachmentRepository = Depends(get_attachment_repo)
) -> AttachmentService:
    return AttachmentService(attachment_repo=repository, s3_client=get_public_s3_client())


def get_private_attachment_service(
        repository: AttachmentRepository = Depends(get_attachment_repo)
) -> AttachmentService:
    return AttachmentService(attachment_repo=repository, s3_client=get_private_s3_client())


def get_user_service(
        session: AsyncSession = Depends(get_db),
        attachment_service: AttachmentService = Depends(get_pubic_attachment_service),
) -> UserService:
    return UserService(session, attachment_service)


class CurrentUser(BaseModel):
    """Авторизованный пользователь, который делает запрос к сервису"""

    user_id: UUID
    username: str | None = None
    full_name: str | None = None
    email: EmailStr
    role: UserRole


def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
) -> CurrentUser:
    """Получение текущего авторизованного пользователя"""

    payload = validate_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token: missing sub claim")
    return CurrentUser(
        user_id=user_id,
        username=payload.get("username"),
        full_name=payload.get("fullname"),
        email=payload.get("email"),
        role=payload.get("role"),
    )


def get_pagination(
        page: int = Query(1, ge=1, description="Страница"),
        limit: int = Query(10, ge=1, le=50, description="Количество элементов на странице")
) -> tuple[int, int]:
    return page, limit
