from uuid import UUID

from src.iam.domain.authz import Subject
from src.shared.domain.events import EventPublisher
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404

from ..domain.entities import Comment, Reaction
from ..domain.repos import CommentRepository, ReactionRepository
from ..schemas import ReactionResponse


class ReactionService:
    def __init__(
            self,
            uow: UnitOfWork,
            comment_repo: CommentRepository,
            reaction_repo: ReactionRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.event_publisher = event_publisher

    async def toggle(
            self,
            comment_id: UUID,
            current_subject: Subject,
            emoji: str,
    ) -> None:
        """Поставить или снять реакцию текущего пользователя."""

        await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        existing = await self.reaction_repo.find(
            comment_id=comment_id, author_id=current_subject.id, emoji=emoji,
        )

        aggregates = [existing]

        if existing is None:
            # Пользователь не оставлял реакции - создаём новую реакцию
            reaction = Reaction.create(
                comment_id=comment_id,
                author_id=current_subject.id,
                emoji=emoji,
            )
            await self.reaction_repo.create(reaction)
            aggregates.append(reaction)

        elif existing.emoji == emoji:
            # Пользователь нажал на ту же реакцию - удаляем
            await self.reaction_repo.delete(existing.id)

        else:
            existing.change(emoji)
            await self.reaction_repo.update(existing)

        await finalize(self.uow, *aggregates, event_publisher=self.event_publisher)

    async def get_reactions_for_comment(
            self, comment_id: UUID, current_subject: Subject,
    ) -> ReactionResponse:

        await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        stats = await self.reaction_repo.get_reaction_stats([comment_id], current_subject.id)

        return ReactionResponse(
            reaction_counts=stats.counts.get(comment_id, {}),
            user_reactions=list(stats.user_reactions.get(comment_id, set())),
        )
