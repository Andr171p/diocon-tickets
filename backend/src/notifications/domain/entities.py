from typing import Any

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ...shared.domain.entities import Entity
from ...shared.utils.time import current_datetime
from .vo import NotificationType


@dataclass(kw_only=True)
class Notification(Entity):
    """
    Уведомление пользователю о событие в системе
    """

    user_id: UUID
    title: str
    message: str
    type: NotificationType
    read: bool = field(default=False)
    data: dict[str, Any] = field(default_factory=dict)  # Дополнительные данные

    def mark_as_read(self) -> None:
        """Пометить как прочитанное"""

        if not self.read:
            self.read = True
            self.updated_at = current_datetime()


@dataclass(kw_only=True)
class UserPreference(Entity):
    """
    Настройки уведомлений для конкретного пользователя
    """

    user_id: UUID
    notification_type: NotificationType

    # По каким каналам получать уведомления
    email_enabled: bool = True
    in_app_enabled: bool = True

    # Дополнительные настройки
    muted_until: datetime | None = None

    def is_enabled_for_channel(self, channel: str) -> bool:
        """
        Проверяет, включён ли канал для данного типа уведомления
        """

        # 1. Если уведомления отключены, то канал недоступен
        if self.muted_until is not None and self.muted_until > current_datetime():
            return False

        # 2. Проверка каналов
        if channel == "email":
            return self.email_enabled
        if channel == "in_app":
            return self.in_app_enabled

        return False

    def disable_channel(self, channel: str) -> None:
        """Отключение уведомлений для конкретного канала"""

        if channel == "email":
            self.email_enabled = False
        elif channel == "in_app":
            self.in_app_enabled = False

        self.updated_at = current_datetime()

    def enable_channel(self, channel: str) -> None:
        """Подключение уведомлений через конкретный канал"""

        if channel == "email":
            self.email_enabled = True
        elif channel == "in_app":
            self.in_app_enabled = True

        self.updated_at = current_datetime()
