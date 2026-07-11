from uuid import UUID

from src.iam.domain.entities import User
from src.iam.mappers import map_user_to_reference
from src.shared.domain.repos import get_or_raise_404
from src.shared.schemas import Page, Pagination

from ..consts import PARTICIPANT_FIELDS
from ..data_loaders import ReferenceLoader
from ..domain.entities import Ticket
from ..domain.repos import TicketFilters, TicketRepository
from ..mappers import map_ticket_to_view_response
from ..schemas import TicketParticipant, TicketViewResponse


def _collect_participants_ids(ticket: Ticket) -> set[UUID]:
    """Собирает уникальные идентификаторы участников заявки."""

    return {
        uid
        for _, field in PARTICIPANT_FIELDS
        if (uid := getattr(ticket, field)) is not None
    }


def _build_participants(ticket: Ticket, users: dict[UUID, User]) -> list[TicketParticipant]:
    participants: dict[UUID, TicketParticipant] = {}

    for role, field in PARTICIPANT_FIELDS:
        user_id = getattr(ticket, field)
        if user_id is None:
            continue

        user = users.get(user_id)
        if user is None:
            continue

        participant = participants.setdefault(
            user.id,
            TicketParticipant(
                ticket_id=ticket.id,
                user=map_user_to_reference(user),
                roles=set(),
            ),
        )
        participant.roles.add(role)

    return list(participants.values())


class TicketQueryService:
    def __init__(
            self,
            ticket_repo: TicketRepository,
            reference_loader: ReferenceLoader
    ) -> None:
        self.ticket_repo = ticket_repo
        self.reference_loader = reference_loader

    async def get_tickets(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[TicketViewResponse]:
        page = await self.ticket_repo.paginate(pagination, filters=filters)

        relations = await self.reference_loader.load(
            users={
                uid
                for ticket in page.items
                for uid in {ticket.reporter_id, ticket.assignee_id}
                if uid
            },
            counterparties={
                ticket.counterparty_id for ticket in page.items if ticket.counterparty_id
            },
            projects={ticket.project_id for ticket in page.items if ticket.project_id},
        )

        def mapper(ticket: Ticket) -> TicketViewResponse:
            return map_ticket_to_view_response(
                ticket=ticket,
                reporter=relations.users.get(ticket.reporter_id),
                assignee=relations.users.get(ticket.assignee_id),
                counterparty=relations.counterparties.get(ticket.counterparty_id),
                project=relations.projects.get(ticket.project_id),
            )

        return page.to_response(mapper)

    async def get_ticket_participants(self, ticket_id: UUID) -> list[TicketParticipant]:
        """Получить участников тикета."""

        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)

        users = _collect_participants_ids(ticket)
        references = await self.reference_loader.load(users=users)

        return _build_participants(ticket, references.users)

    async def get_my_tickets(self) -> Page[TicketViewResponse]:
        """
        Получение списка 'моих' тикетов.
        Для клиентов - по инициатору, для поддержки - по назначению.
        """
