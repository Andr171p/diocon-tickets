from .domain.entities import Feedback
from .schemas import FeedbackResponse


def map_feedback_to_response(feedback: Feedback) -> FeedbackResponse:
    """
    Преобразовать доменный отзыв в API-схему.
    """

    return FeedbackResponse(
        id=feedback.id,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        ticket_id=feedback.ticket_id,
        author_id=feedback.author_id,
        rating=feedback.rating.value,
        comment=feedback.comment,
    )
