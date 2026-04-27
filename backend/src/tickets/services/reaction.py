from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.schemas import CurrentUser
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ..domain.entities import Reaction
from ..domain.repos import CommentRepository, ReactionRepository
from ..domain.vo import ReactionType
from ..schemas import ReactionResponse


class ReactionService:
    def __init__(
            self,
            session: AsyncSession,
            comment_repo: CommentRepository,
            reaction_repo: ReactionRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.event_publisher = event_publisher

    async def toggle(
            self,
            comment_id: UUID,
            current_user: CurrentUser,
            reaction_type: ReactionType,
    ) -> None:
        """Поставить или снять реакцию текущего пользователя"""

        # 1. Проверка комментария на существование
        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка - есть ли уже оставленная реакция от текущего пользователя
        existing_reaction = await self.reaction_repo.find(
            comment_id=comment_id, author_id=current_user.user_id, reaction_type=reaction_type
        )
        if existing_reaction is not None:
            # 2.1 Снятие старой реакции (для переключения на новую)
            await self.reaction_repo.delete(existing_reaction.id)
            if existing_reaction.reaction_type != reaction_type:
                reaction = Reaction.create(
                    comment_id=comment_id,
                    author_id=current_user.user_id,
                    author_role=current_user.role,
                    reaction_type=reaction_type,
                )
                await self.reaction_repo.create(reaction)
        else:
            # 2.2 Создание новой реакции
            reaction = Reaction.create(
                comment_id=comment_id,
                author_id=current_user.user_id,
                author_role=current_user.role,
                reaction_type=reaction_type,
            )
            await self.reaction_repo.create(reaction)

        await self.session.commit()

        # 3. Публикация доменных событий
        for event in reaction.collect_events():
            await self.event_publisher.publish(event)

    async def get_reactions_for_comment(
            self, comment_id: UUID, current_user: CurrentUser
    ) -> ReactionResponse:
        """Получение реакции для комментария"""

        # 1. Проверка существования комментария
        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        reaction_counts = await self.reaction_repo.get_counts([comment_id])
        user_reactions = await self.reaction_repo.get_user_reactions(
            comment_ids=[comment_id], author_id=current_user.user_id
        )

        return ReactionResponse(
            reaction_counts=reaction_counts.get(comment_id, {}),
            user_reactions=list(user_reactions.get(comment_id, [])),
        )
