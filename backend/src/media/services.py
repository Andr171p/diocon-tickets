from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from .constants import PRESIGNED_URL_EXPIRES_IN
from .domain.entities import Attachment
from .domain.ports import AttachmentRepository, Storage
from .schemas import ConfirmUploadRequest, PresignedUploadRequest, PresignedUploadResponse


class AttachmentService:
    def __init__(
            self, session: AsyncSession, storage: Storage, repository: AttachmentRepository
    ) -> None:
        self.session = session
        self.storage = storage
        self.repository = repository

    async def create_presigned_upload_url(
            self, request: PresignedUploadRequest
    ) -> PresignedUploadResponse:
        """Создание подписанного URL для прямой загрузки файла в хранилище"""

        # 1. Создание уникального ключа
        extension = Path(request.filename).suffix.lower()
        unique_name = f"{uuid4()}.{extension}"
        storage_key = f"{request.owner_type}/{request.owner_id}/{unique_name}"

        # 2. Генерация подписанного URL для загрузки
        presigned_url = await self.storage.create_presigned_upload_url(
            storage_key=storage_key,
            content_type=request.content_type,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )

        # 3. Формирование ответа
        return PresignedUploadResponse(
            upload_url=presigned_url, storage_key=storage_key, expires_in=PRESIGNED_URL_EXPIRES_IN,
        )

    async def confirm_upload(self, request: ConfirmUploadRequest, uploaded_by_id: UUID):
        """Подтверждение загрузки файла"""

        # 1. Получение размера файла из хранилища
        file_info = await self.storage.get_file_info(request.storage_key)
        size_bytes = file_info["size"]

        # 2. Создание доменной сущности вложения
        attachment = Attachment(
            original_filename=request.original_filename,
            mime_type=request.content_type,
            size_bytes=size_bytes,
            storage_key=request.storage_key,
            owner_type=request.owner_type,
            owner_id=request.owner_id,
            uploaded_at=...,
            uploaded_by_id=uploaded_by_id,
        )
        await self.repository.create(attachment)
