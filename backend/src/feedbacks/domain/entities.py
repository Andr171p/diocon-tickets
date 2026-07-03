from dataclasses import dataclass
from uuid import UUID
from typing import Self

from src.shared.domain.entities import AggregateRoot
from src.shared.utils.time import current_datetime

from .events import FeedbackCreated


@dataclass(kw_only=True)
class Feedback(AggregateRoot):
    """
    Отзыв клиента о качестве облуживания по закрутому тикету.
    """
    
    ticket_id: UUID
    author_id: UUID
    rating: int
    comment: str | None = None

    def __post_init__(self) -> None:
        """
        Проверка инвариантов отзыва после создания объекта.
        Нормализует комментарий и гарантирует, что оценка находится
        в допустимом диапазоне.
        """

        self._validate_rating(self.rating)
        self.comment = self._normalize_comment(self.comment)

    @classmethod
    def create(
        cls, 
        *, 
        ticket_id: UUID, 
        author_id: UUID, 
        rating: int, 
        comment: str | None = None
    ) -> Self:
        """
        Создаёт новый отзыв клиента.
        """

        feedback = cls(
            ticket_id=ticket_id,
            author_id=author_id,
            rating=rating,
            comment=comment,
        )

        feedback.register_event(
            FeedbackCreated(
                feedback_id=feedback.id,
                ticket_id=ticket_id,
                author_id=author_id,
                rating=feedback.rating,
                comment=feedback.comment,
            )
        )

        return feedback
    
    def edit(
        self,
        *,
        rating: int | None = None,
        comment: str | None = None,
    ) -> None:
        """
        Редактирует оценку и комментарий отзыва.
        Если данные изменились, то обновляет updated_at.
        """

        is_edited = False

        if rating is not None and rating != self.rating:
            self._validate_rating(rating)
            self.rating = rating
            is_edited = True

        if comment is not None:
            normalized_comment = self._normalize_comment(comment)

            if normalized_comment != self.comment:
                self.comment = normalized_comment
                is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def archive(self) -> None:
        """
        Архивирует отзыв через мягкое удаление.
        """

        if self.is_deleted:
            return
        
        self.deleted_at = current_datetime()
        self.updated_at = current_datetime()

    @staticmethod
    def _validate_rating(rating: int) -> None:
        """
        Проверяет, что оценка находиться в диапазоне от 1 до 5.
        """

        if rating < 1 or rating > 5:
            raise ValueError("Feedback ratings must be between 1 and 5")
        
    @staticmethod
    def _normalize_comment(comment: str | None) -> str | None:
        """
        Убирает лишние пробелы из комментария.
        """

        if comment is None:
            return None
        
        normalized = comment.strip()
        return normalized or None