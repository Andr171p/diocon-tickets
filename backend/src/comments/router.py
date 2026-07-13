from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject
from src.shared.dependencies import PaginationDep
from src.shared.schemas import Page

from .dependencies import CommentServiceDep, ReactionServiceDep, VisibleParam, get_comment_or_404
from .schemas import (
    CommentCreate,
    CommentResponse,
    CommentWithReactionsResponse,
    NewCommentText,
    ReactionEmoji,
    ReactionResponse,
)

router = APIRouter(prefix="/comments", tags=["Комментарии"])


@router.get(
    path="/{comment_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_subject)],
    response_model=CommentResponse,
    summary="Получить комментарий",
)
async def get_comment(comment: CommentResponse = Depends(get_comment_or_404)) -> CommentResponse:
    return comment


@router.get(
    path="/{comment_id}/replies",
    status_code=status.HTTP_200_OK,
    response_model=Page[CommentWithReactionsResponse],
    summary="Получить ответы на комментарий",
)
async def get_comment_replies(
        comment_id: UUID,
        pagination: PaginationDep,
        service: CommentServiceDep,
        current_subject: CurrentSubjectDep,
        visible: VisibleParam,
) -> Page[CommentWithReactionsResponse]:
    return await service.get_comment_replies(
        comment_id=comment_id,
        pagination=pagination,
        current_subject=current_subject,
        visible=visible,
    )


@router.post(
    path="/{comment_id}/replies",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Ответить на комментарий",
)
async def create_comment_reply(
        comment_id: UUID,
        data: CommentCreate,
        service: CommentServiceDep,
        current_subject: CurrentSubjectDep,
) -> CommentResponse:
    return await service.add_reply(
        comment_id=comment_id, data=data, current_subject=current_subject,
    )


@router.patch(
    path="/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Отредактировать комментарий",
    response_model=CommentResponse,
)
async def update_comment(
        comment_id: UUID,
        new_text: NewCommentText,
        service: CommentServiceDep,
        current_subject: CurrentSubjectDep,
) -> CommentResponse:
    return await service.edit_comment(
        comment_id=comment_id, new_text=new_text, current_subject=current_subject,
    )


@router.delete(
    path="/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить комментарий",
)
async def delete_comment(
        comment_id: UUID, service: CommentServiceDep, current_subject: CurrentSubjectDep,
) -> None:
    return await service.delete_comment(comment_id=comment_id, current_subject=current_subject)


@router.post(
    path="/{comment_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Переключить реакцию",
    description="""\
    ## Реализует 3 сценария:

     - Создание новой реакции
     - Переключение между реакциями (реакция была создана, пользователь нажал на другую)
     - Удаление реакции (пользователь нажал на поставленную реакцию)
    """
)
async def toggle_reaction(
        comment_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ReactionServiceDep,
        emoji: ReactionEmoji,
) -> None:
    return await service.toggle(
        comment_id=comment_id, emoji=emoji, current_subject=current_subject,
    )


@router.get(
    path="/{comment_id}/reactions",
    status_code=status.HTTP_200_OK,
    response_model=ReactionResponse,
    summary="Получить реакции на комментарий"
)
async def get_comment_reactions(
        comment_id: UUID, current_subject: CurrentSubjectDep, service: ReactionServiceDep,
) -> ReactionResponse:
    return await service.get_reactions_for_comment(comment_id, current_subject)
