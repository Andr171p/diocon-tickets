from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, NonNegativeFloat

from ..iam.domain.vo import UserRole
from ..media.schemas import AttachmentResponse
from .domain.vo import CommentType, ProjectRole, ProjectStatus, TicketPriority, TicketStatus


class TicketPreview(BaseModel):
    """
    Схема превью тикета. Удобно для пагинации, списков, множественного просмотра.
    """

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    reporter_id: UUID = Field(..., description="ID пользователя - инициатора")
    number: str = Field(..., description="Номер тикета", examples=["РОМ-26-00012456"])
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


class TicketBase(BaseModel):
    """Базовые поля для API схем тикета"""

    project_id: UUID | None = Field(
        None, description="ID проекта, к которому нужно привязать тикет"
    )
    reporter_id: UUID = Field(..., description="ID пользователя - инициатора")
    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Описание проблемы")
    priority: TicketPriority = Field(
        ..., description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)",
    )
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому привязан тикет")
    counterparty_name: str | None = Field(
        None, description="Наименование контрагента, нужно для генерации уникального номера"
    )
    tags: list[Tag] = Field(
        default_factory=list, description="Теги для упрощения поиск аи фильтрации"
    )


class TicketResponse(TicketBase):
    """API схема ответа тикета"""

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by_role: UserRole = Field(..., description="Роль пользователя, который создал тикет")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    number: str = Field(..., description="Номер тикета", examples=["РОМ-26-00012456"])
    status: TicketStatus = Field(..., description="Текущий статус")
    assigned_to: UUID | None = Field(None, description="Кому назначен тикет")
    closed_at: datetime | None = Field(None, description="Дата закрытия тикета")

    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Прикреплённые файлы"
    )
    comments: list[CommentResponse] = Field(
        default_factory=list, description="Последние N комментариев"
    )
    history: list[HistoryEntryResponse] = Field(
        default_factory=list, description="История работы с тикетом"
    )


class TicketCreate(TicketBase):
    """Создание тикета"""

    priority: TicketPriority = Field(
        TicketPriority.MEDIUM,
        description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)"
    )


class FilterParams(BaseModel):
    """Параметры для фильтрации тикетов"""

    status: TicketStatus | None = Field(None, description="Фильтрация по статусу")
    priority: TicketPriority | None = Field(None, description="Фильтрация по приоритету")


class TicketPredict(BaseModel):
    """Авто-определение приоритетов + генерация тегов"""

    title: str = Field(..., description="Заголовок тикета")
    description: str = Field(..., description="Описание тикета")


class PredictionConfidence(BaseModel):
    """Уверенность в генерации"""

    priority: NonNegativeFloat = Field(
        ..., le=1.0, description="Уверенность в определении приоритета"
    )
    tags: NonNegativeFloat = Field(..., le=1.0, description="Уверенность в определении тегов")


class PredictionResponse(BaseModel):
    """API схема ответа с определённым приоритетом и сгенерированными тегами"""

    suggested_priority: TicketPriority = Field(..., description="Предложенный приоритет")
    suggested_tags: list[Tag] = Field(
        default_factory=list, min_length=1, max_length=10, description="Предложенные теги"
    )
    confidence: PredictionConfidence = Field(..., description="Уверенность в генерации")


class ProjectBase(BaseModel):
    """Базовая схема проекта"""

    name: str = Field(
        ..., description="Наименование проекта", examples=["Корпоративный сайт компании"]
    )
    key: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Уникальный ключ проекта",
        examples=["PROJ", "MOB1"],
    )
    description: str | None = Field(
        None, description="Описание проекта (рекомендуется к заполнению)"
    )
    counterparty_id: UUID | None = Field(
        None, description="Контрагент для которого реализуется проект"
    )
    owner_id: UUID = Field(..., description="Владелец проекта (обычно support и выше)")


class ProjectCreate(ProjectBase):
    """Схема для создания проекта"""


class ParticipantResponse(BaseModel):
    """Участник проекта"""

    user_id: UUID = Field(..., description="ID пользователя в системе")
    project_role: ProjectRole = Field(..., description="Роль в проекте")
    added_at: datetime = Field(..., description="Дата добавления в проект")
    added_by: UUID = Field(..., description="ID пользователя, который добавил участника")


class ProjectResponse(ProjectBase):
    """API схема ответа для проекта"""

    id: UUID = Field(..., description="Уникальный ID проекта")
    created_at: datetime = Field(..., description="Дата создания проекта")
    updated_at: datetime = Field(..., description="Дата обновления проекта")
    created_by: UUID = Field(..., description="ID пользователя создавшего проект")
    status: ProjectStatus = Field(..., description="Статус проекта")
    participants: list[ParticipantResponse] = Field(
        default_factory=list, description="Участники проекта"
    )


class KeyCheckResponse(BaseModel):
    """Результат проверки уникальности ключа"""

    available: bool = Field(..., description="Доступен ли ключ")
    suggestions: list[str] = Field(
        default_factory=list, description="Варианты, которые можно попробовать "
    )
