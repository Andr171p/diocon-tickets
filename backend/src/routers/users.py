from fastapi import APIRouter, Depends, status

from ..dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.post(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUser,
    summary="Получить информацию о себе"
)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user
