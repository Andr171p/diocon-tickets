from .domain.entities import Ticket
from .schemas import TicketPreview, TicketResponse


def map_ticket_to_preview(ticket: Ticket) -> TicketPreview:
    return TicketPreview(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        created_by=ticket.created_by,
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
    )


def map_ticket_to_response(ticket: Ticket) -> TicketResponse: ...
