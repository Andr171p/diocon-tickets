from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt


class PresignedUploadRequest(BaseModel):
    """Запрос для загрузки файла"""

    filename: str = Field(..., min_length=1, max_length=255, description="Имя файла")
    content_type: str = Field(
        ...,
        pattern=r"^[\w\-]+/[\w\-\.]+$",
        description="Тип контента файла",
        examples=["application/pdf"]
    )
    owner_type: str = Field(
        ...,
        pattern="^(ticket|comment|user|counterparty|message)$",
        description="Сущность, которой принадлежит файл"
    )
    owner_id: UUID = Field(..., description="ID сущности, которой принадлежит файл")


class PresignedUploadResponse(BaseModel):
    """API схема ответа для подписанного URL"""

    upload_url: str = Field(..., description="URL адрес на который нужно загрузить файл")
    storage_key: str = Field(..., description="Уникальный ключ загружаемого объекта")
    expires_in: PositiveInt = Field(
        ..., description="Временной промежуток в формате Timestamp, через который истекает ссылка"
    )


class ConfirmUploadRequest(BaseModel):
    """Подтверждение загрузки"""

    storage_key: str = Field(
        ..., min_length=1, max_length=255, description="Уникальный ключ загруженного объекта")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    content_type: str = Field(
        ...,
        pattern=r"^[\w\-]+/[\w\-\.]+$",
        description="Тип контента файла",
        examples=["application/pdf"],
    )
    owner_type: str = Field(
        ...,
        pattern="^(ticket|comment|user|counterparty|message)$",
        description="Сущность, которой принадлежит файл",
    )
    owner_id: UUID = Field(..., description="ID сущности, которой принадлежит файл")


class AttachmentResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_key: str
    owner_type: str
    owner_id: UUID
    uploaded_by_id: UUID
    uploaded_at: datetime
    preview_url: str | None = None
    full_url: str | None = None
