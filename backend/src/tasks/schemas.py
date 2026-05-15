from typing import Annotated, Literal

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, Field, NonNegativeFloat

from ..media.schemas import AttachmentResponse
from ..tickets.domain.vo import TicketPriority
from .domain.vo import TaskStatus

NewStatus = Annotated[
    TaskStatus, Body(..., embed=True, description="Новый статус задачи")
]
AssigneeId = Annotated[
    UUID,
    Body(..., embed=True, description="ID пользователя, которого нужна назначить исполнителем")
]


class TaskBase(BaseModel):
    """Базовая API схема задачи"""

    ticket_id: UUID | None = Field(None, description="Тикет на основе которого создана задача")
    project_id: UUID | None = Field(None, description="Проект в рамках которого создана задача")
    title: str = Field(..., description="Тема задачи")
    description: str | None = Field(None, description="Постановка задачи")
    priority: TicketPriority = Field(..., description="Приоритет задачи")
    story_points: int | None = Field(
        ...,
        ge=1,
        le=21,
        description="Оценка сложности задачи, где 1 очень легко, а 21 максимально сложная"
    )
    assignee_id: UUID | None = Field(None, description="Исполнитель задачи")
    reviewer_id: UUID | None = Field(None, description="Ответственный за задачу")
    estimated_hours: Decimal | None = Field(
        None, description="Предварительная оценка трудозатрат в часах"
    )
    due_date: date | None = Field(None, description="Срок выполнения (deadline)")


class TaskCreate(TaskBase):
    """API схема для создания задачи"""

    mark_as_todo: bool = Field(False, description="Готова ли задача к выполнению")


class TaskResponse(TaskBase):
    """API схема ответа задачи"""

    id: UUID = Field(..., description="Уникальный ID задачи")
    created_at: datetime = Field(..., description="Дата создания задачи")
    updated_at: datetime = Field(..., description="Дата обновления задачи")
    is_archived: bool = Field(..., description="Перенесена ли задача в архив")
    number: str = Field(
        ...,
        description="Уникальный номер задачи",
        examples=["PRJ-26-00000001-001", "TASK-001"]
    )
    status: TaskStatus = Field(..., description="Текущий cтатус задачи")
    actual_hours: Decimal = Field(..., description="Потрачено часов (факт)")
    started_at: datetime | None = Field(None, description="Дата начала выполнения задачи")
    completed_at: datetime | None = Field(None, description="Дата завершения задачи")
    created_by: UUID = Field(..., description="Пользователь создавший задачу")
    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Медиа контент приложенный к задаче"
    )


class TaskEdit(BaseModel):
    """API схема для редактирования задачи"""

    title: str | None = Field(None, description="Тема задачи")
    description: str | None = Field(None, description="Формулировка задачи")
    priority: TicketPriority | None = Field(None, description="")
    story_points: int | None = Field(
        None,
        ge=1,
        le=21,
        description="Story points для оценки сложности задачи"
    )
    estimated_hours: NonNegativeFloat | None = Field(
        None, description="Предварительное время выполнения"
    )
    due_date: date | None = Field(None, description="Срок выполнения (deadline)")


class TaskReview(BaseModel):
    """API схема для ревью задачи"""

    action: Literal["approve", "reject"] = Field(..., description="Принять или отклонить задачу")
