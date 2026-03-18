from fastapi import APIRouter, Depends, File, UploadFile, status

from ..dependencies import CurrentUser, get_current_user, get_user_service
from ..schemas import UserResponse
from ..services import UserService

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.post(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUser,
    summary="Получить информацию о себе"
)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user


@router.post(
    path="/me/avatar",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    responses={
        201: {"description": "Аватар успешно загружен"},
        400: {"description": "Неверный формат файла или размер превышен"},
        413: {"description": "Файл слишком большой"}
    },
    summary="Загрузка/обновление аватара текущего пользователя"
)
async def upload_my_avatar(
        current_user: CurrentUser = Depends(get_current_user),
        file: UploadFile = File(..., description="Изображение для аватара"),
        service: UserService = Depends(get_user_service)
) -> UserResponse:
    return await service.upload_avatar(current_user.user_id, file)
