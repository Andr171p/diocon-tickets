from typing import ClassVar

import logging
from uuid import UUID

from ..shared.domain.events import Event
from .channels import NotificationChannel
from .domain.vo import NotificationType
from .policies import NotificationPolicy

logger = logging.getLogger(__name__)


class ChannelResolver:
    def __init__(self, *channels: NotificationChannel) -> None:
        self.channels = {type(channel): channel for channel in channels}

    async def resolve(self, notification_type: NotificationType) -> list[NotificationChannel]:
        """Возвращает список каналов, на которые нужно отправить уведомление"""


class TargetResolver:
    """
    Отвечает за определение получателей уведомлений
    """

    polices: ClassVar[dict[type[Event], NotificationPolicy]] = {}

    def registry_policy(self, event_type: type[Event], policy: NotificationPolicy) -> None:
        self.polices[event_type] = policy

    async def get_targets(self, event: Event) -> list[UUID]:
        policy = self.polices.get(type(event))
        if policy is None:
            logger.warning("No notification policy for event %s", type(event).__name__)
            return []

        return await policy.get_targets(event)
