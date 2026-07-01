from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.domain.vo import Priority, Tag
from src.shared.schemas import Page, Pagination

from .entities import Task
from .vo import TaskNumber, TaskStatus


@dataclass(frozen=True)
class TaskView:
    """
    Модель представления задачи (лёгкая модель для чтения)
    """

    id: UUID
    created_at: datetime
    updated_at: datetime

    number: TaskNumber
    title: str
    status: TaskStatus
    priority: Priority
    assignee_id: UUID | None = None
    due_date: datetime | None = None
    story_points: Decimal | None = None

    project_id: UUID | None = None
    ticket_id: UUID | None = None

    tags: set[Tag] = field(default_factory=set)


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

    async def get_grouped_by_status(
            self,
            pagination: Pagination,
            *,
            project_id: UUID | None = None,
            ticket_id: UUID | None = None,
            assignee_id: UUID | None = None,
            # Дополнительные фильтры
            priorities: list[Priority] | None = None,
            overdue_only: bool = False,
    ) -> dict[TaskStatus, Page[TaskView]]:
        """
        Группировка задач по статусам.
        Учитывает переданное пространство имён, если project_id is None -
        вернуться все строке где project_id равен None.
        Возвращает облегченные модели представления задач.
        """
