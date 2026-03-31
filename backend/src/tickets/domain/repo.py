from typing import override

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Comment, Ticket
from .vo import TicketPriority, TicketStatus


class TicketRepository(Repository[Ticket]):
    @override
    async def read(self, ticket_id: UUID, comments_limit: int = 10) -> Ticket | None:
        """
        Получение тикета с лимитом на количество комментариев (для производительности)
        """

    async def get_by_counterparty(
            self,
            counterparty_id: UUID,
            params: PageParams,
            ticket_status: TicketStatus | None = None,
            ticket_priority: TicketPriority | None = None,
    ) -> Page[Ticket]:
        """Получение всех тикетов, принадлежащих контрагенту"""

    async def get_by_creator(
            self,
            user_id: UUID,
            params: PageParams,
            ticket_status: TicketStatus | None = None,
            ticket_priority: TicketPriority | None = None,
    ) -> Page[Ticket]:
        """Получение тикетов, принадлежащих их создателю"""

    async def get_comments(self, ticket_id: UUID, params: PageParams) -> Page[Comment]:
        """Получение комментариев для тикета"""
