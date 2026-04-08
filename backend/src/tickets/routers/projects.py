from uuid import UUID

from fastapi import APIRouter, Query, status

from ...shared.domain.exceptions import NotFoundError
from ..dependencies import ProjectRepoDep, ProjectServiceDep
from ..mappers import map_project_to_response
from ..schemas import KeyCheckResponse, ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Проекты"])


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=list[str],
    summary="Предлагает ключ для проекта",
    description="Генерирует читабельный ключ для проекта, например - 'CP'"
)
def get_key_suggestion(name: str = Query(..., description="Наименование проекта")) -> list[str]:
    ...


@router.get(
    path="/keys/{key}",
    status_code=status.HTTP_200_OK,
    response_model=KeyCheckResponse,
    summary="Проверка доступности ключа"
)
async def check_project_key(key: str, service: ProjectServiceDep) -> KeyCheckResponse:
    return await service.check_key(key)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    responses={
        201: {"description": "Проект успешно создан"},
        409: {"description": "Ключ уже занят (не получилось разрешить конфликт уникальности)"},
    },
    summary="Создание проекта",
)
async def create_project(data: ProjectCreate, service: ProjectServiceDep) -> ProjectResponse:
    return await service.create(data)


@router.get(
    path="/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Получение проекта"
)
async def get_project(project_id: UUID, repository: ProjectRepoDep) -> ProjectResponse:
    project = await repository.read(project_id)
    if project is None:
        raise NotFoundError(f"Project with ID {project_id} not found")
    return map_project_to_response(project)
