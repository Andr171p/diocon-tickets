from .domain.entities import Ticket
from .schemas import TicketParticipantRole

AGGREGATE_TYPE = Ticket.__name__.lower()

# Поля участников заявки
PARTICIPANT_FIELDS: tuple[tuple[TicketParticipantRole, str], ...] = (
    (TicketParticipantRole.CREATOR, "created_by"),
    (TicketParticipantRole.REPORTER, "reporter_id"),
    (TicketParticipantRole.ASSIGNEE, "assignee_id"),
    (TicketParticipantRole.APPROVER, "approved_by"),
    (TicketParticipantRole.RESOLVER, "resolved_by"),
    (TicketParticipantRole.CLOSER, "closed_by"),
)
