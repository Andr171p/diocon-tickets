from typing import override

from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from .dtos import CommentVisibilityPolicy, ReactionStats
from .entities import Comment, Reaction
from .vo import AggregateReference


class CommentRepository(Repository[Comment]):

    @override
    async def paginate(
            self,
            pagination: Pagination,
            aggregate_ref: AggregateReference | None = None,
            policy: CommentVisibilityPolicy | None = None,
    ) -> Page[Comment]: ...

    async def get_replies(
        self,
        comment_id: UUID,
        pagination: Pagination,
        *,
        policy: CommentVisibilityPolicy | None = None,
    ) -> Page[Comment]:
        """
        Получение вложенных ответов на комментарий (дерево комментариев).
        """


class ReactionRepository(Repository[Reaction]):

    async def find(self, comment_id: UUID, author_id: UUID, emoji: str) -> Reaction | None: ...

    async def get_reaction_stats(self, comment_ids: list[UUID], user_id: UUID) -> ReactionStats:
        """
        Получить агрегированные данные о реакциях для каждого комментария из списка.
        """

    async def get_counts(self, comment_ids: list[UUID]) -> dict[UUID, dict[str, int]]:
        """
        Получение счётчиков реакций для комментариев.
        Принимает список ID комментариев для избежания N+1.
        Маппинг: реакция -> количество ('like' -> 5).
        """

    async def get_user_reactions(
            self, comments_ids: list[UUID], author_id: UUID
    ) -> dict[UUID, set[str]]:
        """
        Получение реакций пользователя на комментарии.
        Принимает список ID комментариев для избежания N+1.
        На выходе маппинг Comment ID -> ['like', 'in_progress', ..., 'resolved'].
        """
