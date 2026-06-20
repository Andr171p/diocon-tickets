from fastapi import APIRouter, Depends, status

from src.shared.schemas import Page

from ..dependencies import (
    ActiveUserDep,
    UserByIdDep,
    UsersPageDep,
    get_current_subject,
)
from ..schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Получить информацию о своём учётной записи"
)
async def get_me(user: ActiveUserDep) -> UserResponse:
    return user


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserResponse],
    dependencies=[Depends(get_current_subject)],
    summary="Получить всех пользователей",
)
async def get_users(page: UsersPageDep) -> Page[UserResponse]:
    return page


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    dependencies=[Depends(get_current_subject)],
    summary="Получить пользователя",
)
async def get_user(user: UserByIdDep) -> UserResponse:
    return user
