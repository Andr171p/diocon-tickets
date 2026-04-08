from typing import override

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Comment, Project, Ticket
from .vo import ProjectKey, TicketPriority, TicketStatus


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
            status: TicketStatus | None = None,
            priority: TicketPriority | None = None,
    ) -> Page[Ticket]:
        """Фильтрация тикетов"""

    async def get_comments(self, ticket_id: UUID, params: PageParams) -> Page[Comment]:
        """Получение комментариев для тикета"""


class ProjectRepository(Repository[Project]):

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        """Получение проекта по его уникальному ключу"""

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        """
        Возвращает множество ключей, которые уже существуют.
        Оптимизировано для пакетной проверки.
        """
