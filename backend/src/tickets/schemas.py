from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt

from src.crm.schemas import CounterpartyReference
from src.iam.domain.vo import UserRole
from src.iam.schemas import UserReference
from src.media.schemas import AttachmentResponse
from src.projects.schemas import ProjectReference
from src.shared.domain.vo import Priority

from .domain.vo import TicketStatus, TicketType


class Tag(BaseModel):
    """Теги для упрощения поиска и фильтрации"""

    name: str = Field(
        ..., description="Название тега", examples=["Инцидент", "Вопрос от пользователя"]
    )
    color: str = Field(..., description="Hex код цвета (для UI)", examples=["#0345fc", "#fc0303"])


class TicketBase(BaseModel):
    """Базовые поля для API схем тикета"""

    reporter_id: UUID = Field(..., description="ID пользователя - инициатора")
    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Описание проблемы")
    type: TicketType = Field(..., description="Вид тикета")
    priority: Priority = Field(
        ..., description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)",
    )
    project_id: UUID | None = Field(
        None, description="ID проекта, к которому нужно привязать тикет"
    )
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому привязан тикет")
    product_id: UUID | None = Field(
        None, description="Программный продукт к которому привязан тикет"
    )
    tags: list[Tag] = Field(
        default_factory=list, description="Теги для упрощения поиска и фильтрации"
    )


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
    type: TicketType = Field(..., description="Тип заявки")
    status: TicketStatus = Field(..., description="Текущий статус")
    priority: Priority = Field(..., description="Приоритет")


class TicketViewResponse(BaseModel):
    """
    Облегчённая модель данных для представления тикета
    """

    id: UUID = Field(description="Уникальный ID тикета")
    created_at: datetime = Field(description="Дата создания")
    updated_at: datetime = Field(description="Дата последнего обновления")

    reporter: UserReference = Field(description="Инициатор заявки")
    assignee: UserReference | None = Field(None, description="Исполнитель заявки")

    counterparty: CounterpartyReference | None = Field(None, description="Контрагент заявки")
    project: ProjectReference | None = Field(
        None, description="Проект, которому принадлежит заявка",
    )

    number: str = Field(..., description="Номер тикета", examples=["РОМ-26-00012456"])
    title: str = Field(..., description="Заголовок тикета")
    type: TicketType = Field(..., description="Тип заявки")
    status: TicketStatus = Field(..., description="Текущий статус")
    priority: Priority = Field(..., description="Приоритет")


class TicketResponse(TicketBase):
    """API схема ответа тикета"""

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by_role: UserRole = Field(..., description="Роль пользователя, который создал тикет")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    number: str = Field(..., description="Номер тикета", examples=["ROMASHKA-26-00012456"])
    status: TicketStatus = Field(..., description="Текущий статус")
    assignee_id: UUID | None = Field(None, description="Кому назначен тикет")
    closed_at: datetime | None = Field(None, description="Дата закрытия тикета")
    is_archived: bool = Field(..., description="Заархивирован ли тикет")

    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Прикреплённые файлы"
    )


class TicketCreate(TicketBase):
    """
    Схема поддерживает 3 сценария создания тикета.
    В зависимости от переданных полей система определяет тип создаваемого тикета.

    ### 1. Внутренний тикет

    Создаётся, если **не переданы** ни проект, ни контрагент.
    Используется для задач внутри команды поддержки.

    ### 2. Тикет записывается контрагенту

    Создаётся, если передано поле: counterparty_id.
    Используется при обращении внешнего клиента.

    ### 3. Тикет в рамках проекта

    Создаётся, если передано поле: project_id.
    Используется для задач, связанных с конкретным проектом разработки.
    """

    priority: Priority = Field(
        Priority.MEDIUM,
        description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)"
    )


class TicketAssign(BaseModel):
    """Назначение тикета на пользователя"""

    assignee_id: UUID = Field(..., description="ID пользователя, на которого назначается тикет")


class TicketStatusChange(BaseModel):
    """Изменение статуса тикета"""

    status: TicketStatus = Field(..., description="Статус, который нужно установить")


class TicketUpdate(BaseModel):
    """Редактирование тикета"""

    title: str | None = Field(None, description="Заголовок")
    description: str | None = Field(None, description="Описание")
    priority: Priority | None = Field(None, description="Приоритет")
    tags: list[Tag] | None = Field(None, description="Теги")


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

    suggested_priority: Priority = Field(..., description="Предложенный приоритет")
    suggested_tags: list[Tag] = Field(
        default_factory=list, min_length=1, max_length=10, description="Предложенные теги"
    )
    confidence: PredictionConfidence = Field(..., description="Уверенность в генерации")


class CommentCreate(BaseModel):
    """Создание комментария"""

    text: str = Field(..., description="Текст комментария")
    type: CommentType = Field(CommentType.PUBLIC, description="Тип комментария")


class CommentEdit(BaseModel):
    """Редактирование комментария"""

    text: str = Field(..., description="Новый текст комментария")


class TicketParticipantRole(StrEnum):
    """Роль участника внутри заявки."""

    CREATOR = auto()
    REPORTER = auto()
    ASSIGNEE = auto()
    APPROVER = auto()
    RESOLVER = auto()
    CLOSER = auto()


class TicketParticipant(BaseModel):
    """Участник тикета."""

    ticket_id: UUID = Field(description="Идентификатор заявки")
    user: UserReference = Field(description="Ссылка на пользователя")
    roles: set[TicketParticipantRole] = Field(description="Роль участника в рамках заявки")
