from uuid import UUID

from fastapi import APIRouter, status

from .schemas import AssigneeId, NewStatus, TaskResponse, TaskReview

router = APIRouter(prefix="/tasks", tags=["Задания сотрудникам"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskResponse,
    summary="Создать задачу"
)
async def create_task() -> TaskResponse: ...


@router.patch(
    path="/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Редактировать задачу"
)
async def edit_task(task_id: UUID) -> TaskResponse: ...


@router.post(
    path="/{task_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Сменить статус"
)
async def move_task_status(task_id: UUID, new_status: NewStatus) -> TaskResponse: ...


@router.post(
    path="/{task_id}/assign",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Назначить исполнителя"
)
async def assign_task(task_id: UUID, assignee_id: AssigneeId) -> TaskResponse: ...


@router.post(
    path="/{task_id}/request-review",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Запросить ревью"
)
async def request_task_review(task_id: UUID) -> TaskResponse: ...


@router.post(
    path="/{task_id}/review",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Провести ревью",
)
async def review_task(task_id: UUID, data: TaskReview) -> TaskResponse: ...


@router.delete(
    path="/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Архивировать задачу"
)
async def archive_task(task_id: UUID) -> TaskResponse: ...
