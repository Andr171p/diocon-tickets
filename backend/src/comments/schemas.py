from typing import Annotated

from datetime import datetime
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, Field, NonNegativeInt

from src.media.schemas import AttachmentResponse

from .domain.vo import CommentVisibility

ReactionEmoji = Annotated[str, Body(embed=True, description="Реакция пна комментарий")]
NewCommentText = Annotated[str, Body(embed=True, description="Текст комментария")]


class CommentCreate(BaseModel):
    """Создать комментарий."""

    text: str = Field(description="Текст комментария")
    visibility: CommentVisibility = Field(description="Область видимости комментария")


class CommentResponse(BaseModel):
    """Модель представления комментария."""

    id: UUID = Field(description="Уникальный идентификатор комментария")
    created_at: datetime = Field(description="Дата создания")
    updated_at: datetime = Field(description="Дата последнего обновления")

    author_id: UUID = Field(description="Идентификатор пользователя, который оставил комментарий")
    text: str = Field(description="Текст комментария")
    visibility: CommentVisibility = Field(description="Область видимости комментария")

    parent_comment_id: UUID | None = Field(
        None, description="Комментарий на который был сделан ответ",
    )
    reply_count: NonNegativeInt = Field(description="Количество ответов")

    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Медиа контент внутри тикета"
    )


class ReactionResponse(BaseModel):
    """Сводка реакций для одного комментария."""

    reaction_counts: dict[str, NonNegativeInt] = Field(
        default_factory=dict,
        description="Счётчик для каждой оставленной реакции",
        examples=[{"like": 17, "fire": 2, "heart": 1}],
    )
    user_reactions: list[str] = Field(
        default_factory=list, description="Реакции, которые оставил текущий пользователь"
    )


class CommentWithReactionsResponse(CommentResponse, ReactionResponse):
    """Комментарий с реакциями."""
