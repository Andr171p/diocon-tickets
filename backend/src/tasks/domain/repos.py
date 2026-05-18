from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Task
from .vo import TaskNumber


class TaskRepository(Repository[Task]):

    async def get_by_number(self, number: TaskNumber) -> Task | None:
        """Получение задачи по её уникальному номеру"""

    async def get_next_sequence(
            self, ticket_id: UUID | None = None, project_id: UUID | None = None
    ) -> int:
        """
        Получение общего количества задач.
        Поддерживает 2 сценария:
         - Получение количества задач привязанных к тикету (передан ticket_id)
         - Получение количества внутренних задач (ticket_id = None),
          только те задачи, которые не принадлежат тикету
        """
