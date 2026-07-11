from typing import Annotated

from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from fastapi import Depends, Query

from src.shared.dependencies import PaginationDep, SessionDep
from src.shared.schemas import Page

from .domain.dtos import ActivityLogFilters
from .domain.repos import ActivityLogRepository
from .infra.repos import SqlActivityLogRepository
from .mappers import map_activity_log_to_response
from .recorder import ActivityLogRecorder
from .schemas import ActivityLogResponse

ActivityLogPaginatorFunc = Callable[[str, UUID], Awaitable[Page[ActivityLogResponse]]]


def get_activity_log_repo(session: SessionDep) -> SqlActivityLogRepository:
    return SqlActivityLogRepository(session)


ActivityLogRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_log_repo)]


def get_activity_log_recorder(activity_log_repo: ActivityLogRepoDep) -> ActivityLogRecorder:
    return ActivityLogRecorder(activity_log_repo)


ActivityLogRecorderDep = Annotated[ActivityLogRepository, Depends(get_activity_log_recorder)]


def get_activity_log_filters(
        actor_id: UUID | None = Query(None, description="Субъект выполнивший действие"),
        actions: list[str] | None = Query(None, min_length=1, description="Список действий"),
        occurred_after: datetime | None = Query(None, description="Произошло после"),
        occurred_before: datetime | None = Query(None, description="Произошло до")
) -> ActivityLogFilters:
    return ActivityLogFilters(
        actor_id=actor_id,
        actions=actions,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
    )


ActivityLogFiltersDep = Annotated[ActivityLogFilters, Depends(get_activity_log_filters)]


async def paginate_activity_logs(
        activity_log_repo: ActivityLogRepoDep,
        aggregate_type: str,
        aggregate_id: UUID,
        pagination: PaginationDep,
        filters: ActivityLogFiltersDep,
) -> Page[ActivityLogResponse]:
    page = await activity_log_repo.get_for_aggregate(
        aggregate_type, aggregate_id, pagination=pagination, filters=filters,
    )
    return page.to_response(map_activity_log_to_response)


async def get_activity_logs_paginator(  # noqa: RUF029
        activity_log_repo: ActivityLogRepoDep,
        pagination: PaginationDep,
        filters: ActivityLogFiltersDep,
) -> ActivityLogPaginatorFunc:
    async def paginator(aggregate_type: str, aggregate_id: UUID) -> Page[ActivityLogResponse]:
        page = await activity_log_repo.get_for_aggregate(
            aggregate_type,
            aggregate_id,
            pagination=pagination,
            filters=filters,
        )
        return page.to_response(map_activity_log_to_response)

    return paginator
