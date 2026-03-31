from fastapi import APIRouter, status

router = APIRouter(prefix="/tickets", tags=["Тикеты"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=...,
    summary="Создание тикета"
)
async def create_ticket(): ...
