from dataclasses import dataclass
from uuid import UUID

from .vo import CommentVisibility


@dataclass(frozen=True, slots=True)
class CommentVisibilityPolicy:
    """Политика для фильтрации комментариев по области видимости."""

    viewer_id: UUID | None
    visible: set[CommentVisibility]

    def __post_init__(self) -> None:
        if self.viewer_id is None and CommentVisibility.NOTE in self.visible:
            raise ValueError("Author ID required for received NOTE comments")


@dataclass(frozen=True, slots=True)
class ReactionStats:
    """Агрегированные данные о реакциях на комментарии."""

    counts: dict[UUID, dict[str, int]]
    user_reactions: dict[UUID, set[str]]
