from fastapi import APIRouter, status

from ..dependencies import CurrentUserDep
from ..schemas import CurrentUser

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUser,
    summary="Получить информацию о себе"
)
async def get_me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user
