from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Ticket


class TicketRepository(Repository[Ticket]):

    async def get_by_counterparty(self, counterparty_id: UUID) -> ...:
        """Получение всех тикетов, принадлежащих контрагенту"""

    async def get_by_creator(self, user_id: UUID) -> ...:
        """Получение тикетов, принадлежащих их создателю"""

    async def get_ticket_comments(self, ticket_id: UUID, include: ...) -> ...:
        """Получение комментариев """
