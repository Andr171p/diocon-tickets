from uuid import UUID

from fastapi import APIRouter, status

from src.comments.dependencies import CommentServiceDep, VisibleParam
from src.comments.domain.vo import AggregateReference, AggregateType
from src.comments.schemas import CommentCreate, CommentResponse, CommentWithReactionsResponse
from src.iam.dependencies import CurrentSubjectDep
from src.shared.dependencies import PaginationDep
from src.shared.schemas import Page

router = APIRouter(prefix="/tickets", tags=["Комментарии заявки"])


@router.get(
    path="/{ticket_id}/comments",
    status_code=status.HTTP_200_OK,
    response_model=Page[CommentWithReactionsResponse],
    summary="Получить комментарии заявки"
)
async def get_ticket_comments(
        ticket_id: UUID,
        pagination: PaginationDep,
        current_subject: CurrentSubjectDep,
        service: CommentServiceDep,
        visible: VisibleParam,
) -> Page[CommentWithReactionsResponse]:
    return await service.get_comments(
        aggregate_ref=AggregateReference(id=ticket_id, type=AggregateType.TICKET),
        pagination=pagination,
        current_subject=current_subject,
        visible=visible,
    )


@router.post(
    path="/{ticket_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Оставить комментарий к заявке",
)
async def create_ticket_comment(
        ticket_id: UUID,
        data: CommentCreate,
        current_subject: CurrentSubjectDep,
        service: CommentServiceDep,
) -> CommentResponse:
    return await service.create_comment(
        aggregate_ref=AggregateReference(id=ticket_id, type=AggregateType.TICKET),
        data=data,
        current_subject=current_subject,
    )
