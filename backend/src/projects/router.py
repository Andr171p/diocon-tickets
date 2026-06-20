from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject, require_role
from src.iam.domain.constants import SUPPORT_MANAGER_OR_ABOVE
from src.shared.schemas import Page

from .dependencies import (
    MyProjectsDep,
    ProjectDep,
    ProjectPageDep,
    ProjectServiceDep,
)
from .schemas import (
    KeyCheckResult,
    ProjectCreate,
    ProjectMembershipCreate,
    ProjectMembershipResponse,
    ProjectResponse,
)
from .utils import generate_project_key

router = APIRouter(prefix="/projects", tags=["Проекты"])


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Предлагает ключ проекта",
    description="Генерирует человекочитаемый ключ проекта, например - `CP`"
)
def get_key_suggestion(
        name: str = Query(..., description="Наименование проекта"),
) -> dict[str, str]:
    return {"key": generate_project_key(name)}


@router.get(
    path="/keys/{key}",
    status_code=status.HTTP_200_OK,
    response_model=KeyCheckResult,
    dependencies=[Depends(require_role(SUPPORT_MANAGER_OR_ABOVE))],
    summary="Проверяет свободен ли ключ"
)
async def check_project_key(key: str, service: ProjectServiceDep) -> KeyCheckResult:
    return await service.check_key(key)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    summary="Создаёт новый проект",
    description="Проекты могут создавать только внутренние сотрудники",
    responses={
        201: {"description": "Проект успешно создан."},
        409: {"description": "Ключ уже занят (не удалось разрешить конфликт уникальности)."},
        403: {"description": "Недостаточно прав для создания проекта (недоступно для клиентов)."},
    },
)
async def create_project(
        current_subject: CurrentSubjectDep, data: ProjectCreate, service: ProjectServiceDep
) -> ProjectResponse:
    return await service.create(data, current_subject)


@router.get(
    path="/my",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectResponse],
    summary="Получение моих проектов",
    description="""\
    Получение проектов пользователя в зависимости от параметра role:

     - `owner` - проекты, где пользователь является владельцем.
     - `member` - пользователь любой другой участник, кроме владельца.
     - `all` - любой участник (на важно какая роль).
    """,
)
async def get_my_projects(my_projects: MyProjectsDep) -> Page[ProjectResponse]:
    return my_projects


@router.get(
    path="/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    dependencies=[Depends(get_current_subject)],
    summary="Получить проект",
)
async def get_project(project: ProjectDep) -> ProjectResponse:
    return project


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectResponse],
    dependencies=[Depends(require_role(SUPPORT_MANAGER_OR_ABOVE))],
    summary="Получить все проекты"
)
async def get_projects(page: ProjectPageDep) -> Page[ProjectResponse]:
    return page


@router.post(
    path="/{project_id}/memberships",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectMembershipResponse,
    summary="Добавить участника в проект"
)
async def create_project_membership(
        project_id: UUID,
        data: ProjectMembershipCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectMembershipResponse:
    return await service.add_member(project_id, data, current_subject)


@router.delete(
    path="/{project_id}/memberships/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника из проекта"
)
async def delete_project_membership(
        project_id: UUID,
        user_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> None:
    return await service.remove_member(project_id, user_id, current_subject)
