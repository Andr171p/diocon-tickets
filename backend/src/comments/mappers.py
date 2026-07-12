from src.media.mappers import map_attachment_to_response

from .domain.entities import Comment
from .schemas import CommentResponse, CommentWithReactionsResponse


def map_comment_to_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author_id=comment.author_id,
        text=comment.text,
        visibility=comment.visibility,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
    )


def map_comment_with_reactions_to_response(
        comment: Comment,
        reaction_counts: dict[str, int],
        user_reactions: list[str]
) -> CommentWithReactionsResponse:
    return CommentWithReactionsResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author_id=comment.author_id,
        text=comment.text,
        visibility=comment.visibility,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
        reaction_counts=reaction_counts,
        user_reactions=user_reactions,
    )
