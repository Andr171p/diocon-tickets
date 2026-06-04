from fastapi import APIRouter, status

router = APIRouter(
    prefix="/timesheets", tags=["Листы учёта рабочего времени", "🕓 Учёт рабочего времени"]
)


@router.get(
    path="/my",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Учёт рабочего времени пользователя"
)
async def get_my_timesheets(): ...
