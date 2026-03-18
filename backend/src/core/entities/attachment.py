# Модель для работы с файловыми вложениями

from uuid import UUID

from pydantic import Field, PositiveInt

from .base import Entity


class Attachment(Entity):
    """Файловые вложения"""

    entity_type: str = Field(
        ...,
        description="Тип сущности к которой привязан файл",
        examples=["user_avatar", "ticket", "counterparty_avatar"]
    )
    entity_id: UUID = Field(..., description="ID сущности, которой принадлежит файл")
    file_name: str = Field(..., description="Имя файла в хранилище")
    original_name: str = Field(..., description="Оригинальное имя файла")
    object_key: str = Field(..., description="Уникальный ключ объекта в S3 хранилище")
    public_url: str | None = Field(None, description="Публичный URL адрес объекта")
    mime_type: str = Field(..., description="MIME тип файла")
    size_bytes: PositiveInt = Field(..., description="Размер файла в байтах")
    uploaded_by: UUID = Field(..., description="ID пользователя, который загрузил файл")
    is_deleted: bool = Field(False, description="Удалён ли файл из хранилища")
