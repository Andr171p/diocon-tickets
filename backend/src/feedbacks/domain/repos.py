from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from .entities import Feedback


@dataclass(frozen=True)
class FeedbackFilters:
    """
    Фильтры для списка отзывов.
    Используется поддержкой для просмотра клиенткого удовлетворённости.
    """

    rating: int | None = None
    ticket_id: UUID | None = None
    author_id: UUID | None = None


class FeedbackRepository(Repository[Feedback]):
    """
    Конткракт репозитория для работа с отзывами.
    """

    async def get_by_ticket(self, ticket_id: UUID) -> Feedback | None:
        """
        Получить активный отзыв по тикету.
        Возвращает None, если отзыв не найден или архивирован.
        """

    async def paginate(
            self,
            pagination: Pagination,
            filters: FeedbackFilters | None = None,
    ) -> Page[Feedback]:
        """
        Получить страницу активных отзывов с опциональными фильтрами.
        """