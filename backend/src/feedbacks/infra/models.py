from uuid import UUID

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class FeedbackOrm(Base):
    """
    ORM-модель клиенткого отзыва по тикету.
    """

    __tablename__ = "feedbacks"

    ticket_id: Mapped[UUID] = mapped_column(nullable=False)
    author_id: Mapped[UUID] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("ticket_id", name="uq_feedbacks_ticket_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedbacks_rating_range"),
    )