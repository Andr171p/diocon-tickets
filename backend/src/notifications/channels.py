from typing import Protocol

import logging
from uuid import UUID

from ..iam.domain.repos import UserRepository
from ..shared.domain.exceptions import EmailSendingFailedError
from ..shared.infra.mail import SmtpMailSender
from ..shared.infra.websocket import WebsocketManager
from .domain.entities import Notification
from .domain.exceptions import NotificationSendingFailedError
from .domain.vo import NotificationType

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    async def send(self, user_id: UUID, notification: Notification) -> None:
        """Отправить уведомление через текущий канал"""


# Маппинг типов уведомлений к email шаблону
EMAIL_TEMPLATE_MAP: dict[NotificationType, str] = {
}


class EmailChannel:
    def __init__(self, mail_sender: SmtpMailSender, user_repo: UserRepository) -> None:
        self.mail_sender = mail_sender
        self.user_repo = user_repo

    async def send(self, user_id: UUID, notification: Notification) -> None:
        user = await self.user_repo.read(user_id)
        if user is None:
            return
        template_name = EMAIL_TEMPLATE_MAP.get(notification.type)
        if template_name is None:
            logger.warning(
                "No such template registered for this notification type - '%s'",
                notification.type.value
            )
        try:
            await self.mail_sender.send(
                to=user.email,
                subject=notification.title,
                plain_text=notification.message,
                template_name=template_name,
                context=None if template_name is None else notification.data,
            )
        except EmailSendingFailedError as e:
            raise NotificationSendingFailedError(
                "Error occurred while sending to email channel"
            ) from e


class WebsocketChannel:
    def __init__(self, ws_manager: WebsocketManager) -> None:
        self.ws_manager = ws_manager

    async def send(self, user_id: UUID, notification: Notification) -> None:
        payload = {
            "type": "notification",
            "notification": {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "read": notification.read,
                "data": notification.data,
                "created_at": notification.created_at,
            }
        }
        await self.ws_manager.send_to_user(user_id, payload)


class ChannelResolver:
    def __init__(self, *channels: NotificationChannel) -> None:
        self.channels = {type(channel): channel for channel in channels}

    async def resolve(self, notification_type: NotificationType) -> list[NotificationChannel]:
        """Возвращает список каналов, на которые нужно отправить уведомление"""
