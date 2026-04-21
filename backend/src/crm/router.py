from typing import Annotated, Any

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from ..iam.dependencies import get_current_user, require_role
from ..iam.domain.constants import CUSTOMER_ADMIN_AND_ABOVE, SUPPORT_MANAGER_OR_ABOVE, SUPPORT_TEAM
from ..iam.mappers import map_user_to_response
from ..iam.schemas import UserResponse
from ..shared.dependencies import PageParamsDep
from ..shared.domain.exceptions import NotFoundError
from ..shared.schemas import Page
from .dependencies import CounterpartyRepoDep, CounterpartyServiceDep
from .mappers import map_counterparty_to_response
from .schemas import BranchAdd, CounterpartyCreate, CounterpartyResponse

router = APIRouter(prefix="/counterparties", tags=["Контрагенты"])


@router.post(
    path="",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Создание контрагента",
)
async def create_counterparty(
        data: CounterpartyCreate, service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.create(data)


@router.get(
    path="/{counterparty_id}",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)],
    summary="Получение контрагента",
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
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
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
    response_model=Page[CounterpartyResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение списка контрагентов",
)
async def get_counterparties(
        params: PageParamsDep, repository: CounterpartyRepoDep
) -> dict[str, Any]:
    page = await repository.paginate(params)
    return page.to_response(map_counterparty_to_response)


@router.delete(
    path="/{counterparty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(*SUPPORT_MANAGER_OR_ABOVE))],
    summary="Удаление контрагента",
    description="Soft-delete метод, делает контрагента не активным не удаляя фактически"
)
async def delete_counterparty(counterparty_id: UUID, repository: CounterpartyRepoDep) -> None:
    await repository.update(counterparty_id, is_active=False)


@router.get(
    path="/{counterparty_id}/customers",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserResponse],
    dependencies=[Depends(require_role(*CUSTOMER_ADMIN_AND_ABOVE))],
    summary="Получение клиентов контрагента",
    description="Доступно с ролью `customer_admin` и выше",
)
async def get_counterparty_customers(
        counterparty_id: UUID, params: PageParamsDep, repository: CounterpartyRepoDep
) -> Page[dict[str, Any]]:
    page = await repository.get_customers(counterparty_id, params)
    return page.to_response(map_user_to_response)
