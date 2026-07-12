from uuid import UUID

from src.iam.domain.authz import Subject
from src.iam.domain.exceptions import PermissionDeniedError
from src.shared.domain.events import EventPublisher
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404
from src.shared.schemas import Page, Pagination

from ..domain.authz import can_create_comment, can_edit_or_remove_comment
from ..domain.dtos import CommentVisibilityPolicy
from ..domain.entities import Comment
from ..domain.repos import CommentRepository, ReactionRepository
from ..domain.services import remove_comment
from ..domain.vo import AggregateReference, CommentVisibility
from ..mappers import map_comment_to_response, map_comment_with_reactions_to_response
from ..schemas import CommentCreate, CommentResponse, CommentWithReactionsResponse


class CommentService:
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

    async def create_comment(
            self, aggregate_ref: AggregateReference, data: CommentCreate, current_subject: Subject,
    ) -> CommentResponse:
        permission = can_create_comment(current_subject, data.visibility)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        comment = Comment.create(
            aggregate_type=aggregate_ref.type,
            aggregate_id=aggregate_ref.id,
            author_id=current_subject.id,
            text=data.text,
            visibility=data.visibility,
        )
        await self.comment_repo.create(comment)
        await finalize(self.uow, comment, event_publisher=self.event_publisher)

        return map_comment_to_response(comment)

    async def add_reply(
            self,
            comment_id: UUID,
            data: CommentCreate,
            current_subject: Subject,
    ) -> CommentResponse:
        permission = can_create_comment(current_subject, data.visibility)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        comment = await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        reply = comment.create_reply(
            author_id=current_subject.id,
            text=data.text,
            visibility=data.visibility,
        )
        await self.comment_repo.create(reply)
        await finalize(self.uow, reply, event_publisher=self.event_publisher)

        return map_comment_to_response(reply)

    async def edit_comment(
            self, comment_id: UUID, new_text: str, current_subject: Subject,
    ) -> CommentResponse:
        """Отредактировать комментарий."""

        comment = await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        permission = can_edit_or_remove_comment(current_subject, comment)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        comment.edit(new_text=new_text, edited_by=current_subject.id)
        await self.comment_repo.update(comment)
        await finalize(self.uow, comment, event_publisher=self.event_publisher)

        return map_comment_to_response(comment)

    async def delete_comment(self, comment_id: UUID, current_subject: Subject) -> None:

        comment = await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        permission = can_edit_or_remove_comment(current_subject, comment)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        parent = None
        if comment.is_reply:
            parent = await self.comment_repo.read(comment.parent_comment_id)

        remove_comment(comment, parent)
        await self.comment_repo.update(comment)

        if parent:
            await self.comment_repo.update(parent)

        await finalize(self.uow, comment, event_publisher=self.event_publisher)

    async def get_comments(
            self,
            aggregate_ref: AggregateReference,
            pagination: Pagination,
            current_subject: Subject,
            visible: set[CommentVisibility],
    ) -> Page[CommentWithReactionsResponse]:
        """Получить список родителей комментариев."""

        policy = CommentVisibilityPolicy(viewer_id=current_subject.id, visible=visible)
        page = await self.comment_repo.paginate(
            pagination, aggregate_ref=aggregate_ref, policy=policy,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_subject.id)

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
            visible: set[CommentVisibility],
    ) -> Page[CommentWithReactionsResponse]:
        """Получить дерево ответов комментария."""

        parent = await get_or_raise_404(self.comment_repo.read, comment_id, Comment)

        policy = CommentVisibilityPolicy(viewer_id=current_subject.id, visible=visible)
        page = await self.comment_repo.get_replies(
            comment_id=parent.id, pagination=pagination, policy=policy,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_subject.id)

        def mapper(comment: Comment) -> CommentWithReactionsResponse:
            return map_comment_with_reactions_to_response(
                comment=comment,
                reaction_counts=stats.counts.get(comment.id, {}),
                user_reactions=list(stats.user_reactions.get(comment.id, set())),
            )

        return page.to_response(mapper)
