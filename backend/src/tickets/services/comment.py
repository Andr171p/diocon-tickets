from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.domain.authz import Subject
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import Page, Pagination

from ..domain.entities import Comment, Ticket
from ..domain.repos import CommentRepository, ReactionRepository, TicketRepository
from ..domain.vo import CommentType
from ..mappers import map_comment_to_response, map_comment_with_reactions_to_response
from ..schemas import CommentCreate, CommentEdit, CommentResponse, CommentWithReactionsResponse


class CommentService:
    def __init__(
            self,
            session: AsyncSession,
            ticket_repo: TicketRepository,
            comment_repo: CommentRepository,
            reaction_repo: ReactionRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.ticket_repo = ticket_repo
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.event_publisher = event_publisher

    @staticmethod
    def _prepare_comment(
            ticket: Ticket,
            current_subject: Subject,
            text: str,
            comment_type: CommentType,
            parent_comment: Comment | None = None,
    ) -> tuple[Comment, Comment | None]:
        """
        Подготовка комментария к записи в хранилище.
        Возвращает кортеж из нового комментария и его родителя.
        """

        if parent_comment is None:
            comment = Comment.create(
                ticket_id=ticket.id,
                author_id=current_subject.id,
                text=text,
                comment_type=comment_type,
            )
            return comment, None

        # 3. Создание ответа на комментарий
        reply = parent_comment.create_reply(
            author_id=current_subject.id,
            text=text,
            comment_type=comment_type,
        )

        return reply, parent_comment

    async def add_comment(
            self, ticket_id: UUID, data: CommentCreate, current_subject: Subject,
    ) -> CommentResponse:
        """Добавление комментария к тикету"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Создание и сохранение комментария
        comment, _ = self._prepare_comment(
            ticket=ticket,
            current_subject=current_subject,
            text=data.text,
            comment_type=data.type,
        )
        await self.comment_repo.create(comment)
        await self.ticket_repo.update(ticket)
        await self.session.commit()

        # 3. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def reply_to_comment(
            self,
            ticket_id: UUID,
            parent_comment_id: UUID,
            data: CommentCreate,
            current_subject: Subject,
    ) -> CommentResponse:
        """Добавление ответа на комментарий"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Получение родительского комментария
        parent_comment = await self.comment_repo.read(parent_comment_id)
        if parent_comment is None:
            raise NotFoundError(f"Comment with ID {parent_comment_id} not found")

        # 3. Проверка на, что комментарий принадлежит тикету
        if parent_comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        # 4. Создание и сохранение ответа
        reply, parent_comment = self._prepare_comment(
            ticket=ticket,
            current_subject=current_subject,
            text=data.text,
            comment_type=data.type,
            parent_comment=parent_comment,
        )
        await self.comment_repo.update(parent_comment)
        await self.comment_repo.create(reply)
        await self.ticket_repo.update(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in reply.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(reply)

    async def edit_comment(
            self, ticket_id: UUID, comment_id: UUID, data: CommentEdit, edited_by: UUID
    ) -> CommentResponse:
        """Редактирование комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка на, что комментарий принадлежит тикету
        if comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        comment.edit(new_text=data.text, edited_by=edited_by)
        await self.comment_repo.update(comment)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def delete_comment(
            self, ticket_id: UUID, comment_id: UUID, deleted_by: UUID,
    ) -> None:
        """Удаление комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка на, что комментарий принадлежит тикету
        if comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        # 3. Если выбранный комментарий - ответ, то уменьшение счётчика ответов у родителя
        parent_comment = None
        if comment.is_reply:
            parent_comment = await self.comment_repo.read(comment.parent_comment_id)
            if parent_comment is not None and not parent_comment.is_deleted:
                parent_comment.decrement_reply_count()

        # 3. Удаление и запись в историю
        comment.delete(deleted_by=deleted_by)
        await self.comment_repo.update(comment)

        if parent_comment is not None:
            await self.comment_repo.update(parent_comment)

        await self.ticket_repo.update(ticket)
        await self.session.commit()

    async def get_comments(
            self,
            ticket_id: UUID,
            pagination: Pagination,
            current_subject: Subject,
            include_internal: bool = False,
    ) -> Page[CommentWithReactionsResponse]:
        """Получение комментариев к тикету с учётом прав"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 4. Получение комментариев + загрузка реакций
        page = await self.comment_repo.get_by_ticket(
            ticket_id=ticket_id,
            pagination=pagination,
            user_id=current_subject.id,
            include_notes=True,
            include_internal=include_internal,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_subject.id)

        # 5. Маппинг реакций к комментарию
        def mapper(comment: Comment) -> CommentWithReactionsResponse:
            return map_comment_with_reactions_to_response(
                comment=comment,
                reaction_counts=stats.counts.get(comment.id, {}),
                user_reactions=list(stats.user_reactions.get(comment.id, set())),
            )

        return page.to_response(mapper)

    async def get_comment_replies(
            self,
            comment_id: UUID,
            pagination: Pagination,
            current_subject: Subject,
            include_internal: bool = False,
    ) -> Page[CommentWithReactionsResponse]:
        """Получение дерево ответов на комментарий"""

        # 1. Проверка существования и доступности родителя
        parent_comment = await self.comment_repo.read(comment_id)
        if parent_comment is None or parent_comment.is_deleted:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        ticket = await self.ticket_repo.read(parent_comment.ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {comment_id} not found")

        page = await self.comment_repo.get_replies(
            parent_comment_id=parent_comment.id,
            pagination=pagination,
            user_id=current_subject.id,
            include_internal=include_internal,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_subject.id)

        # 3. Маппинг реакций к комментарию
        def mapper(comment: Comment) -> CommentWithReactionsResponse:
            return map_comment_with_reactions_to_response(
                comment=comment,
                reaction_counts=stats.counts.get(comment.id, {}),
                user_reactions=list(stats.user_reactions.get(comment.id, set())),
            )

        return page.to_response(mapper)
