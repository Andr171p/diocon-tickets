from uuid import UUID

from fastapi import APIRouter, status

from src.iam.dependencies import CurrentSubjectDep

from ..dependencies import ProjectMemberServiceDep
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


@router.delete(
    path="/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника из проекта"
)
async def delete_project_membership(
        project_id: UUID,
        user_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
) -> None:
    return await service.remove_member(project_id, user_id, current_subject)
