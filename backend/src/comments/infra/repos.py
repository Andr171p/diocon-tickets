from typing import override

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from src.media.infra.repo import AttachmentMapper
from src.shared.infra.repos import ModelMapper, SqlAlchemyRepository
from src.shared.schemas import Page, Pagination

from ..domain.dtos import CommentVisibilityPolicy, ReactionStats
from ..domain.entities import Comment, Reaction
from ..domain.vo import AggregateReference, CommentVisibility
from .models import CommentOrm, ReactionOrm


class CommentMapper(ModelMapper[Comment, CommentOrm]):
    @staticmethod
    def to_entity(model: CommentOrm) -> Comment:
        return Comment(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            aggregate=AggregateReference(id=model.aggregate_id, type=model.aggregate_type),
            author_id=model.author_id,
            text=model.text,
            visibility=model.visibility,
            parent_comment_id=model.parent_comment_id,
            reply_count=model.reply_count,
            attachments=[
                AttachmentMapper.to_entity(attachment) for attachment in model.attachments
            ],
        )

    @staticmethod
    def from_entity(entity: Comment) -> CommentOrm:
        return CommentOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            aggregate_id=entity.aggregate.id,
            aggregate_type=entity.aggregate.type,
            author_id=entity.author_id,
            text=entity.text,
            visibility=entity.visibility,
            parent_comment_id=entity.parent_comment_id,
            reply_count=entity.reply_count,
            attachments=[
                AttachmentMapper.from_entity(attachment) for attachment in entity.attachments
            ],
        )


class ReactionMapper(ModelMapper[Reaction, ReactionOrm]):
    @staticmethod
    def to_entity(model: ReactionOrm) -> Reaction:
        return Reaction(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            comment_id=model.comment_id,
            author_id=model.author_id,
            emoji=model.emoji,
        )

    @staticmethod
    def from_entity(entity: Reaction) -> ReactionOrm:
        return ReactionOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            comment_id=entity.comment_id,
            author_id=entity.author_id,
            emoji=entity.emoji,
        )


class SqlCommentRepository(SqlAlchemyRepository[Comment, CommentOrm]):
    model = CommentOrm
    model_mapper = CommentMapper

    def _apply_comment_visibility_policy(
            self, stmt: Select[tuple[CommentOrm]], policy: CommentVisibilityPolicy,
    ) -> Select[tuple[CommentOrm]]:
        conditions = [self.model.visibility == CommentVisibility.PUBLIC]

        if policy.visible:
            if CommentVisibility.NOTE in policy.visible:
                conditions.append(
                    (self.model.visibility == CommentVisibility.NOTE) &
                    (self.model.author_id == policy.viewer_id),
                )
            if CommentVisibility.INTERNAL:
                conditions.append(self.model.visibility == CommentVisibility.INTERNAL)

        return stmt.where(or_(*conditions))

    @override
    async def paginate(
            self,
            pagination: Pagination,
            aggregate_ref: AggregateReference,
            policy: CommentVisibilityPolicy,
    ) -> Page[Comment]:
        stmt = select(self.model)

        conditions = [
            self.model.aggregate_type == aggregate_ref.type,
            self.model.aggregate_id == aggregate_ref.id,
            self.model.parent_comment_id.is_(None),
            self.model.deleted_at.is_(None),
        ]

        stmt = stmt.where(and_(*conditions))

        if policy:
            stmt = self._apply_comment_visibility_policy(stmt, policy)

        return await self._paginate(stmt, pagination)

    async def get_replies(
            self,
            comment_id: UUID,
            pagination: Pagination,
            *,
            policy: CommentVisibilityPolicy | None = None,
    ) -> Page[Comment]:
        conditions = [
            self.model.parent_comment_id == comment_id,
            self.model.deleted_at.is_(None),
        ]

        stmt = select(self.model).where(and_(*conditions))

        if policy:
            stmt = self._apply_comment_visibility_policy(stmt, policy)

        return await self._paginate(stmt, pagination)


class SqlReactionRepository(SqlAlchemyRepository[Reaction, ReactionOrm]):
    model = ReactionOrm
    model_mapper = ReactionMapper

    async def find(
            self, comment_id: UUID, author_id: UUID, emoji: str
    ) -> Reaction | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.comment_id == comment_id) &
                (self.model.author_id == author_id) &
                (self.model.emoji == emoji)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_reaction_stats(self, comment_ids: list[UUID], author_id: UUID) -> ReactionStats:
        stmt = (
            select(
                self.model.comment_id,
                self.model.emoji,
                func.count(self.model.id).label("cnt"),
                func.count(self.model.id)
                .filter(self.model.author_id == author_id)
                .label("user_has_type")
            )
            .where(
                (self.model.comment_id.in_(comment_ids)) &
                (self.model.deleted_at.is_(None))
            )
            .group_by(self.model.comment_id, self.model.emoji)
        )

        result = await self.session.execute(stmt)

        counts: dict[UUID, dict[str, int]] = defaultdict(dict)
        user_reactions: dict[UUID, set[str]] = defaultdict(set)

        for row in result:
            counts[row.comment_id][row.reaction_type] = row.cnt
            if row.user_has_type > 0:
                user_reactions[row.comment_id].add(row.reaction_type)

        return ReactionStats(counts=counts, user_reactions=user_reactions)
