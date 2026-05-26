from uuid import UUID

from ..core.settings import settings
from ..tickets.domain.events import TicketCreated
from .domain.entities import Notification
from .domain.vo import NotificationType


class NotificationFactory:
    """Фабрика для создания уведомлений из доменных событий"""

    @staticmethod
    def from_ticket_created(event: TicketCreated, targets: list[UUID]) -> list[Notification]:
        return [
            Notification(
                user_id=target,
                title="Тикет успешно создан",
                message=f"Тикет #{event.number} «{event.title}» был создан.",
                type=NotificationType.TICKET_CREATED,
                data={
                    "ticket_id": f"{event.ticket_id}",
                    "ticket_number": event.number,
                    "ticket_title": event.title,
                    "ticket_url": f"{settings.frontend_url}/tickets/{event.number}",
                    "support_email": settings.mail.support_email,
                }
            ) for target in targets
        ]
