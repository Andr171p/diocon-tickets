from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Notification, UserPreference
from .vo import NotificationType


class NotificationRepository(Repository[Notification]):

    async def get_unread_count(self, user_id: UUID) -> int:
        """Количество непрочитанных уведомлений"""

    async def get_by_user(
            self, user_id: UUID, params: PageParams, unread_only: bool = False
    ) -> Page[Notification]:
        """Получение уведомлений пользователя"""


class PreferencesRepository(Repository[UserPreference]):

    async def get_for_user(
            self, user_id: UUID, notification_type: NotificationType
    ) -> UserPreference | None:
        """Получение настроек пользователя для конкретного типа уведомлений"""

    async def get_by_user(self, user_id: UUID) -> list[UserPreference]:
        """Получение всех настроек пользователя"""
