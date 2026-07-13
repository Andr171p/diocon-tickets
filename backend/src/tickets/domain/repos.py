from typing import override

from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from .dtos import TicketFilters
from .entities import Ticket


class TicketRepository(Repository[Ticket]):
    @override
    async def paginate(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[Ticket]: ...

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        """
        Получение общего числа тикетов.
        Поддерживает 3 сценария получения количества:
         - Внутренних тикетов (проект и контрагент не указаны)
         - Тикеты в рамках проекта (указан проект + 'опционально' контрагент)
         - Принадлежащие контрагенту (указан контрагент, проект не указан)
        """

    async def get_by_reporter(self, reporter_id: UUID, params: Pagination) -> Page[Ticket]: ...
