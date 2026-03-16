from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dependencies import CurrentUser, get_auth_service, get_current_user, oauth2_scheme
from ..schemas import TokensPair
from ..services import AuthService

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=TokensPair,
    summary="Войти в учётную запись"
)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        service: AuthService = Depends(get_auth_service),
) -> TokensPair:
    return await service.authenticate(form_data.username, form_data.password)
