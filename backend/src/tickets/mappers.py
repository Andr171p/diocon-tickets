from src.crm.domain.entities import Counterparty
from src.crm.schemas import CounterpartyReference
from src.iam.domain.entities import User
from src.iam.schemas import UserReference
from src.media.mappers import map_attachment_to_response
from src.projects.domain.entities import Project
from src.projects.schemas import ProjectReference

from .domain.entities import Comment, Ticket
from .domain.vo import ReactionType
from .schemas import (
    CommentResponse,
    CommentWithReactionsResponse,
    Tag,
    TicketPreview,
    TicketResponse,
    TicketViewResponse,
)


def map_ticket_to_preview(ticket: Ticket) -> TicketPreview:
    return TicketPreview(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        created_by=ticket.created_by,
        reporter_id=ticket.reporter_id,
        number=ticket.number.value,
        title=ticket.title,
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
    )


def map_ticket_to_view_response(
        ticket: Ticket,
        reporter: User,
        assignee: User | None = None,
        counterparty: Counterparty | None = None,
        project: Project | None = None,
) -> TicketViewResponse:
    assignee_ref = (
        UserReference(
            id=assignee.id,
            full_name=assignee.full_name.value,
            email=assignee.email.value,
            type=assignee.type,
        )
        if assignee else None
    )
    counterparty_ref = (
        CounterpartyReference(
            id=counterparty.id,
            name=counterparty.name,
            email=counterparty.email,
        )
        if counterparty else None
    )
    project_ref = (
        ProjectReference(
            id=project.id,
            key=project.key.value,
            name=project.name,
        )
        if project else None
    )

    return TicketViewResponse(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        reporter=UserReference(
            id=reporter.id,
            full_name=reporter.full_name.value,
            email=reporter.email.value,
            type=reporter.type,
        ),
        assignee=assignee_ref,
        counterparty=counterparty_ref,
        project=project_ref,
        number=ticket.number.value,
        title=ticket.title,
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
    )


def map_comment_to_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_role=comment.author_role,
        text=comment.text,
        type=comment.type,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
    )


def map_comment_with_reactions_to_response(
        comment: Comment,
        reaction_counts: dict[ReactionType, int],
        user_reactions: list[ReactionType]
) -> CommentWithReactionsResponse:
    return CommentWithReactionsResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_role=comment.author_role,
        text=comment.text,
        type=comment.type,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
        reaction_counts=reaction_counts,
        user_reactions=user_reactions,
    )


def map_ticket_to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        project_id=ticket.project_id,
        counterparty_id=ticket.counterparty_id,
        product_id=ticket.product_id,
        created_by=ticket.created_by,
        reporter_id=ticket.reporter_id,
        number=ticket.number.value,
        title=ticket.title,
        description=ticket.description,
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
        assignee_id=ticket.assignee_id,
        closed_at=ticket.closed_at,
        is_archived=ticket.is_deleted,
        tags=[Tag(name=tag.name, color=tag.color) for tag in ticket.tags],
        attachments=[map_attachment_to_response(attachment) for attachment in ticket.attachments],
    )
