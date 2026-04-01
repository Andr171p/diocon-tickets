from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..iam.domain.vo import UserRole
from ..media.schemas import AttachmentResponse
from .domain.vo import CommentType, TicketPriority, TicketStatus


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


class CommentResponse(BaseModel):
    """Схема API ответа для комментария"""

    id: UUID = Field(..., description="Уникальный ID комментария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    author_id: UUID = Field(..., description="ID автора (тот кто написал комментарий)")
    author_role: UserRole = Field(..., description="Роль автора в системе")
    text: str = Field(..., description="Текст комментария")
    type: CommentType = Field(..., description="Тип комментария")
    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Медиа контент внутри тикета"
    )


class HistoryEntryResponse(BaseModel):
    """Схема записи истории изменений"""

    created_at: datetime = Field(..., description="Дата записи")
    actor_id: UUID = Field(..., description="ID пользователя, который внёс изменения")
    action: str = Field(
        ...,
        description="Действие, которое было произведено над тикетом",
        examples=["created", "assigned", "status_changed"]
    )
    old_value: str | None = Field(None, description="Старое значение (до изменений)")
    new_value: str | None = Field(None, description="Новое значение")
    description: str = Field(..., description="Человеко-читаемое описание действия")


class Tag(BaseModel):
    """Теги для упрощения поиска и фильтрации"""

    name: str = Field(
        ..., description="Название тега", examples=["Инцидент", "Вопрос от пользователя"]
    )
    color: str = Field(..., description="Hex код цвета (для UI)", examples=["#0345fc", "#fc0303"])


class TicketResponse(BaseModel):
    """API схема ответа тикета"""

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому относится тикет")
    created_by_role: UserRole = Field(..., description="Роль пользователя, который создал тикет")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Детальное описание")
    status: TicketStatus = Field(..., description="Текущий статус")
    priority: TicketPriority = Field(..., description="Приоритет выполнения")
    assigned_to: UUID | None = Field(None, description="Кому назначен тикет")
    closed_at: datetime | None = Field(None, description="Дата закрытия тикета")

    tags: list[Tag] = Field(
        default_factory=list, description="Теги для упрощения поиск аи фильтрации"
    )

    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Прикреплённые файлы"
    )
    comments: list[CommentResponse] = Field(
        default_factory=list, description="Последние N комментариев"
    )
    history: list[HistoryEntryResponse] = Field(
        default_factory=list, description="История работы с тикетом"
    )


class TicketCreate(BaseModel):
    """Создание тикета"""

    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Описание проблемы")
    priority: TicketPriority = Field(
        TicketPriority.MEDIUM,
        description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)"
    )
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому привязан тикет")
    tags: list[Tag] = Field(
        default_factory=list, description="Теги для упрощения поиск аи фильтрации"
    )


class FilterParams(BaseModel):
    """Параметры для фильтрации тикетов"""

    status: TicketStatus | None = Field(None, description="Фильтрация по статусу")
    priority: TicketPriority | None = Field(None, description="Фильтрация по приоритету")
