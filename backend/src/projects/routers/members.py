from uuid import UUID

from fastapi import APIRouter, status
from fastapi.params import Depends

from src.iam.dependencies import CurrentSubjectDep, get_current_subject
from src.shared.schemas import Page

from ..dependencies import ProjectMemberServiceDep, get_member_or_404, paginate_members
from ..schemas import ProjectMemberCreate, ProjectMemberResponse

router = APIRouter(prefix="/projects", tags=["Участники проекта"])


@router.post(
    path="/{project_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectMemberResponse,
    summary="Добавить участника в проект"
)
async def create_project_member(
        project_id: UUID,
        data: ProjectMemberCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
) -> ProjectMemberResponse:
    return await service.add_member(project_id, data, current_subject)


@router.get(
    path="/{project_id}/members",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectMemberResponse],
    dependencies=[Depends(get_current_subject)],
    summary="Получить участников проекта",
)
async def get_project_members(
        members: Page[ProjectMemberResponse] = Depends(paginate_members),
) -> Page[ProjectMemberResponse]:
    return members


@router.get(
    path="/{project_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectMemberResponse,
    dependencies=[Depends(get_current_subject)],
    summary="Получить участника проекта",
)
async def get_project_member(
        member: ProjectMemberResponse = Depends(get_member_or_404),
) -> ProjectMemberResponse:
    return member


@router.delete(
    path="/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника из проекта"
)
async def delete_project_member(
        project_id: UUID,
        user_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
) -> None:
    return await service.remove_member(project_id, user_id, current_subject)
