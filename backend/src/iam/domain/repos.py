from typing import Protocol

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from ..domain.vo import UserRole
from .entities import Invitation, User


class UserRepository(Repository[User]):

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_supports(self, pagination: PageParams) -> Page[User]:
        """
        Получение всех сотрудников поддержки (для ролей SUPPORT_AGENT И SUPPORT_MANAGER)
        """

    async def get_all_support_ids(self) -> list[UUID]:
        """
        Получение всех ID сотрудников поддержки.
        Должен загружать все ID в память.
        """


class TokenBlacklist(Protocol):

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        """Отзыв токена (добавление токена в черный список)"""

    async def is_revoked(self, jti: UUID) -> bool:
        """Проверка токена на отзыв"""


class InvitationRepository(Repository[Invitation]):

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None: ...
