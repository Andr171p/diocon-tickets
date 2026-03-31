from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .domain.vo import TicketPriority, TicketStatus


class TicketPreview(BaseModel):
    """
    Схема превью тикета. Удобно для пагинации, списков, множественного просмотра.
    """

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    title: str = Field(..., description="Заголовок тикета")
    status: TicketStatus = Field(..., description="Текущий статус")
    priority: TicketPriority = Field(..., description="Приоритет")


class TicketResponse(BaseModel):
    """API схема ответа тикета"""


class TicketCreate(BaseModel):
    """Создание тикета"""

    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Описание проблемы")
    priority: TicketPriority
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому привязан тикет")
