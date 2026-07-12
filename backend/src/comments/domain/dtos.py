from dataclasses import dataclass
from uuid import UUID

from .vo import CommentVisibility


@dataclass(frozen=True)
class CommentFilters:
    """Фильтры для получения списка комментариев."""

    author_id: UUID | None = None
    visibilities: set[CommentVisibility] | None = None


@dataclass(frozen=True, slots=True)
class ReactionStats:
    """Агрегированные данные о реакциях на комментарии."""

    counts: dict[UUID, dict[str, int]]
    user_reactions: dict[UUID, set[str]]
