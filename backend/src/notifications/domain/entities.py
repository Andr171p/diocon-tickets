from typing import Any

from dataclasses import dataclass, field
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

        self.read = True
        self.updated_at = current_datetime()
