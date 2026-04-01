from typing import Annotated, Any

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from ..iam.dependencies import get_current_support_user
from ..shared.dependencies import PageParamsDep
from ..shared.domain.exceptions import NotFoundError
from ..shared.schemas import Page
from .dependencies import CounterpartyRepoDep, CounterpartyServiceDep
from .mappers import map_counterparty_to_response
from .schemas import BranchAdd, CounterpartyCreate, CounterpartyResponse

router = APIRouter(
    prefix="/counterparties",
    tags=["Контрагенты"],
    dependencies=[Depends(get_current_support_user)],
)


@router.post(
    path="",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание контрагента"
)
async def create_counterparty(
        data: CounterpartyCreate, service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.create(data)


@router.get(
    path="/{counterparty_id}",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение контрагента"
)
async def get_counterparty(
        counterparty_id: UUID, repository: CounterpartyRepoDep
) -> CounterpartyResponse:
    counterparty = await repository.read(counterparty_id)
    if counterparty is None:
        raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")
    return map_counterparty_to_response(counterparty)


@router.post(
    path="/{counterparty_id}",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление обособленного подразделения",
)
async def add_branch(
        counterparty_id: Annotated[
            UUID,
            Path(..., description="ID контрагента, к которому нужно привязать нового")
        ],
        data: BranchAdd,
        service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.add_branch(counterparty_id, data)


@router.get(
    path="",
    response_model=Page[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Получение списка контрагентов"
)
async def get_counterparties(
        params: PageParamsDep, repository: CounterpartyRepoDep
) -> dict[str, Any]:
    page = await repository.paginate(params)
    return page.to_response(map_counterparty_to_response)


@router.delete(
    path="/{counterparty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление контрагента",
    description="Soft-delete метод, делает контрагента не активным не удаляя физически"
)
async def delete_counterparty(counterparty_id: UUID, repository: CounterpartyRepoDep) -> None:
    await repository.update(counterparty_id, is_active=False)
