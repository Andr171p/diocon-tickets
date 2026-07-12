from fastapi import APIRouter, Depends, Query, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject, require_role
from src.iam.domain.constants import SUPPORT_MANAGER_OR_ABOVE
from src.shared.schemas import Page

from ..dependencies import MyProjectsDep, ProjectDep, ProjectServiceDep, ProjectsPageDep
from ..domain.services import generate_project_key
from ..schemas import KeyCheckResult, ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Проекты"])


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Предлагает ключ проекта",
    description="Генерирует человекочитаемый ключ проекта, например - `PRJ`"
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
    summary="Создать новый проект",
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
    summary="Мои проекты",
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
    summary="Пагинация проектов"
)
async def get_projects(page: ProjectsPageDep) -> Page[ProjectResponse]:
    return page
