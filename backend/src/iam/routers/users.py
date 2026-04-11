from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...shared.domain.exceptions import NotFoundError
from ..dependencies import CurrentUserDep, get_user_repo, require_role
from ..domain.constants import SUPPORT_TEAM
from ..domain.repos import UserRepository
from ..mappers import map_user_to_response
from ..schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Получить информацию о себе"
)
async def get_me(
        current_user: CurrentUserDep, repository: UserRepository = Depends(get_user_repo)
) -> UserResponse:
    user = await repository.read(current_user.user_id)
    return map_user_to_response(user)


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    dependencies=[Depends(require_role(SUPPORT_TEAM))],
    summary="Получение информации об аккаунте",
    description="Доступно только для команды поддержки"
)
async def get_user(
        user_id: UUID, repository: UserRepository = Depends(get_user_repo)
) -> UserResponse:
    user = await repository.read(user_id)
    if user is None:
        raise NotFoundError(f"User with ID {user_id} not found")
    return map_user_to_response(user)
