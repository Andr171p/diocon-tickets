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

    @override
    async def paginate(
            self,
            params: PageParams,
            creator_id: UUID | None = None,
            counterparty_id: UUID | None = None,
            ticket_status: TicketStatus | None = None,
            ticket_priority: TicketPriority | None = None,
    ) -> Page[Ticket]:
        """Фильтрация тикетов"""

    async def get_comments(self, ticket_id: UUID, params: PageParams) -> Page[Comment]:
        """Получение комментариев для тикета"""
