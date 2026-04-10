from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...shared.domain.exceptions import NotFoundError
from ..dependencies import CurrentUserDep, get_current_customer_admin, get_user_repo
from ..domain.repos import UserRepository
from ..mappers import map_user_to_response
from ..schemas import CurrentUser, UserResponse

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUser,
    summary="Получить информацию о себе"
)
async def get_me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    dependencies=[Depends(get_current_customer_admin)],
    summary="Получение информации об аккаунте",
    description="Доступно только для пользователей с ролью `customer_admin` и выше"
)
async def get_user(
        user_id: UUID, repository: UserRepository = Depends(get_user_repo)
) -> UserResponse:
    user = await repository.read(user_id)
    if user is None:
        raise NotFoundError(f"User with ID {user_id} not found")
    return map_user_to_response(user)
