from uuid import UUID

from ..tickets.domain.events import TicketCreated, TicketReassigned
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
                    "title": event.title,
                }
            ) for target in targets
        ]
    
    @staticmethod
    def from_ticket_reassigned(event: TicketReassigned, targets: list[UUID]) -> list[Notification]:
        return [
            Notification(
                user_id=target,
                title="Тикет был переназначен",
                message=(f"Тикет #{event.number} «{event.title}» был переназначен."),  
        
                type=NotificationType.TICKET_REASSIGNED,
                data={
                    "ticket_id": f"{event.ticket_id}",
                    "ticket_number": event.number,
                    "title": event.title,
                    "reassigned_by": f"{event.reassigned_by}",
                    "new_assignee_id": f"{event.new_assignee_id}",
                    "old_assignee_id": f"{event.old_assignee_id}",
                },
            )
            for target in targets
        ]
