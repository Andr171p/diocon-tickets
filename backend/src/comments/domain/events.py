from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event

from .vo import AggregateType


@dataclass(frozen=True, kw_only=True)
class CommentCreated(Event):
    """Комментарий создан."""

    comment_id: UUID
    parent_comment_id: UUID | None = None
    aggregate_type: AggregateType
    aggregate_id: UUID
    author_id: UUID
    is_public: bool


@dataclass(frozen=True, kw_only=True)
class CommentEdited(Event):
    """Комментарий был изменён."""

    comment_id: UUID
    aggregate_type: AggregateType
    aggregate_id: UUID
    edited_by: UUID


@classmethod
class ReactionCreated(Event):
    """Оставлена реакция под комментарием."""

    comment_id: UUID
    author_id: UUID
    emoji: str
