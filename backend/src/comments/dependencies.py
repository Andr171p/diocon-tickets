from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from src.shared.dependencies import EventPublisherDep, SessionDep
from src.shared.domain.repos import get_or_raise_404

from .domain.entities import Comment
from .domain.repos import CommentRepository, ReactionRepository
from .domain.vo import AggregateReference, AggregateType, CommentVisibility
from .infra.repos import SqlCommentRepository, SqlReactionRepository
from .mappers import map_comment_to_response
from .schemas import CommentResponse
from .services import CommentService, ReactionService

VisibleParam = Annotated[
    set[CommentVisibility] | None, Query(None, description="Области видимости")
]


def get_aggregate_ref(aggregate_type: AggregateType, aggregate_id: UUID) -> AggregateReference:
    return AggregateReference(id=aggregate_id, type=aggregate_type)


AggregateRefDep = Annotated[AggregateReference, Depends(get_aggregate_ref)]


def get_comment_repo(session: SessionDep) -> SqlCommentRepository:
    return SqlCommentRepository(session)


def get_reaction_repo(session: SessionDep) -> SqlReactionRepository:
    return SqlReactionRepository(session)


CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repo)]
ReactionRepoDep = Annotated[ReactionRepository, Depends(get_reaction_repo)]


def get_comment_service(
        uow: SessionDep,
        comment_repo: CommentRepoDep,
        reaction_repo: ReactionRepoDep,
        event_publisher: EventPublisherDep,
) -> CommentService:
    return CommentService(
        uow=uow,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=event_publisher,
    )


def get_reaction_service(
        uow: SessionDep,
        comment_repo: CommentRepoDep,
        reaction_repo: ReactionRepoDep,
        event_publisher: EventPublisherDep,
) -> ReactionService:
    return ReactionService(
        uow=uow,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=event_publisher,
    )


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
ReactionServiceDep = Annotated[ReactionService, Depends(get_reaction_service)]


async def get_comment_or_404(comment_id: UUID, comment_repo: CommentRepoDep) -> CommentResponse:
    comment = await get_or_raise_404(comment_repo.read, comment_id, Comment)
    return map_comment_to_response(comment)
