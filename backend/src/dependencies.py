from typing import Annotated

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from .core.entities import UserRole
from .core.errors import UnauthorizedError
from .db.base import session_factory
from .db.repos import CounterpartyRepository
from .services.notification import NotificationService
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


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)


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
        raise UnauthorizedError("Failed to parse JWT claims")
    return CurrentUser(
        user_id=user_id,
        username=payload.get("username"),
        full_name=payload.get("fullname"),
        email=payload.get("email"),
        role=payload.get("role"),
    )
