from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dependencies import AuthServiceDep
from ..schemas import Tokens, TokensRefresh, UserCreateForm

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    path="/register/{token}",
    status_code=status.HTTP_201_CREATED,
    response_model=Tokens,
    summary="Регистрация пользователя по приглашению"
)
async def register(
        token: Annotated[str, Path(..., description="Токен из пригласительного письма")],
        data: UserCreateForm,
        service: AuthServiceDep,
) -> Tokens:
    return await service.register(token, data)


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=Tokens,
    summary="Вход в учётную запись"
)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        service: AuthServiceDep,
) -> Tokens:
    return await service.authenticate(form_data.username, form_data.password)


@router.post(
    path="/refresh",
    status_code=status.HTTP_200_OK,
    response_model=Tokens,
    summary="Обновление пары токенов"
)
async def refresh(data: TokensRefresh, service: AuthServiceDep) -> Tokens:
    return await service.refresh_tokens(data.refresh_token)
