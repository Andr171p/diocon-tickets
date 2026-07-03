from uuid import UUID

from fastapi import APIRouter, status

from src.iam.dependencies import CurrentSubjectDep
from src.shared.dependencies import PaginationDep
from src.shared.schemas import Page

from .dependencies import FeedbackFiltersDep, FeedbackServiceDep
from .schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)

router = APIRouter(prefix="/feedbacks", tags=["Отзывы"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=FeedbackResponse,
    summary="Оставить отзыв по тикету",
)
async def create_feedback(
    data: FeedbackCreate,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.create_feedback(
        data=data,
        current_subject=current_subject,
    )


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse | Page[FeedbackResponse],
    summary="Получить отзыв или список отзывов",
)
async def get_feedbacks(
    pagination: PaginationDep,
    filters: FeedbackFiltersDep,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse | Page[FeedbackResponse]:
    if filters.ticket_id is not None:
        return await service.get_by_ticket(
            ticket_id=filters.ticket_id,
            current_subject=current_subject,
        )
    
    return await service.get_feedbacks(
        pagination=pagination,
        filters=filters,
        current_subject=current_subject,
    )


@router.patch(
    path="/{feedback_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse,
    summary="Обновить отзыв",
)
async def update_feedback(
    feedback_id: UUID,
    data: FeedbackUpdate,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.update(
        feedback_id=feedback_id,
        data=data,
        current_subject=current_subject,
    )


@router.delete(
    path="/{feedback_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse,
    summary="Архивировать отзыв",
)
async def archive_feedback(
    feedback_id: UUID,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.archive(
        feedback_id=feedback_id,
        current_subject=current_subject,
    )