from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Notification


class NotificationRepository(Repository[Notification]):

    async def get_unread_count(self, user_id: UUID) -> int:
        """Количество непрочитанных уведомлений"""

    async def get_by_user(
            self, user_id: UUID, params: PageParams, unread_only: bool = False
    ) -> Page[Notification]:
        """Получение уведомлений пользователя"""
