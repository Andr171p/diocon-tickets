from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...shared.dependencies import PageParamsDep
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page
from ..dependencies import CurrentUserDep, UserRepoDep, require_role
from ..domain.constants import SUPPORT_TEAM
from ..mappers import map_user_to_response
from ..schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Получить информацию о себе"
)
async def get_me(current_user: CurrentUserDep, repository: UserRepoDep) -> UserResponse:
    user = await repository.read(current_user.user_id)
    return map_user_to_response(user)


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение информации об аккаунте",
    description="Доступно только для команды поддержки",
)
async def get_user(user_id: UUID, repository: UserRepoDep) -> UserResponse:
    user = await repository.read(user_id)
    if user is None:
        raise NotFoundError(f"User with ID {user_id} not found")
    return map_user_to_response(user)


@router.get(
    path="/supports",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserResponse],
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение списка сотрудников поддержки",
    description="Доступно только для команды поддержки",
)
async def get_supports(pagination: PageParamsDep, repository: UserRepoDep) -> Page[UserResponse]:
    page = await repository.get_supports(pagination)
    return page.to_response(map_user_to_response)
