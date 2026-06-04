
from datetime import date
from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Timesheet, Worklog


class WorklogRepository(Repository[Worklog]):

    async def get_by_period(
            self, user_id: UUID, period_start: date, period_end: date
    ) -> list[Worklog]: ...

    async def get_by_task(self, task_id: UUID) -> list[Worklog]: ...

    async def get_by_ticket(self, ticket_id: UUID) -> list[Worklog]: ...


class TimesheetRepository(Repository[Timesheet]):
    ...
