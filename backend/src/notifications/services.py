from typing import Any

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.domain.exceptions import NotFoundError
from .channels import ChannelResolver
from .domain.entities import Notification
from .domain.exceptions import NotificationSendingFailedError
from .domain.repo import NotificationRepository
from .domain.vo import NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
            self,
            session: AsyncSession,
            repository: NotificationRepository,
            resolver: ChannelResolver
    ) -> None:
        self.session = session
        self.repository = repository
        self.resolver = resolver

    async def send(
            self,
            user_id: UUID,
            notification_type: NotificationType,
            title: str,
            message: str,
            data: dict[str, Any]
    ) -> None:
        """Отправка уведомления через все подходящие каналы"""

        # 1. Создание и сохранение сущности
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data,
        )
        await self.repository.create(notification)
        await self.session.commit()

        # 2. Отправка уведомления во все подходящие каналы
        channels = await self.resolver.resolve(notification_type)
        for channel in channels:
            try:
                await channel.send(user_id, notification)
            except NotificationSendingFailedError:
                logger.exception("Notification sending failed")

    async def mark_as_read(self, notification_id: UUID) -> None:
        notification = await self.repository.read(notification_id)
        if notification is None:
            raise NotFoundError(f"Notification with ID {notification_id} not found")

        if not notification.read:
            notification.mark_as_read()
            await self.repository.upsert(notification)
            await self.session.commit()
        else:
            logger.warning("Notification with ID %s already marked as read", notification_id)
