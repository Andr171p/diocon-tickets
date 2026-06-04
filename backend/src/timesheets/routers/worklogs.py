from fastapi import APIRouter, status

router = APIRouter(
    prefix="/worklogs", tags=["Журнал проделанных работ", "🕓 Учёт рабочего времени"]
)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=...,
    summary="Записать потраченное время в журнал"
)
async def create_worklog(): ...


@router.get(
    path="/{worklog_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Получить запись о потраченном времени"
)
async def get_worklog(): ...
