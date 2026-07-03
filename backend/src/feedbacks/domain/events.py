from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class FeedbackCreated(Event):
    """
    Клиент оставил отзыв по тикету.
    """

    feedback_id: UUID
    ticket_id: UUID
    author_id: UUID
    rating: int
    comment: str | None = None