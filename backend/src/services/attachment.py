import logging
from uuid import UUID, uuid4

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from ..core.entities import Attachment
from ..core.errors import FileTooLargeError
from ..db.repos import AttachmentRepository
from ..s3 import S3Client

logger = logging.getLogger(__name__)


class AttachmentService:
    def __init__(self, attachment_repo: AttachmentRepository, s3_client: S3Client) -> None:
        self.attachment_repo = attachment_repo
        self.s3_client = s3_client

    async def upload_file(
            self,
            entity_type: str,
            entity_id: UUID,
            file: UploadFile,
            uploaded_by: UUID,
            is_public: bool = False,
            max_size_bytes: int = 10 * 1024 * 1024,
    ) -> Attachment:
        """Универсальный метод для загрузки файловых вложений.

        Важно: метод НЕ делает commit и НЕ откатывает транзакцию!
        Commit / rollback должен выполнять вызывающий код.
        """

        # 1. Валидация входных данных
        if file.filename is None:
            raise ValueError("File name not specified!")
        if file.size is not None and file.size > max_size_bytes:
            raise FileTooLargeError(
                f"File too large (max size - {max_size_bytes // 1024 // 1024} MB)!"
            )
        content = await file.read()
        if len(content) > max_size_bytes:
            raise FileTooLargeError(
                f"File too large (max size - {max_size_bytes // 1024 // 1024} MB)!"
            )

        # 2. Определение необходимых параметров
        original_name = file.filename
        mime_type = file.content_type or "application/octet-stream"
        extension = file.filename.rsplit(".", maxsplit=1)[-1].lower()
        file_name = f"{uuid4().hex}.{extension}"
        object_key = f"{entity_type}/{entity_id}/{file_name}"

        # 3. Загрузка в S3 + формирование публичного URL (если требуется)
        await self.s3_client.upload(content, key=object_key)
        public_url = None
        if is_public:
            public_url = self.s3_client.get_public_url(object_key)

        # 4. Создание записи в БД
        try:
            attachment = Attachment(
                entity_type=entity_type,
                entity_id=entity_id,
                file_name=file_name,
                original_name=original_name,
                object_key=object_key,
                public_url=public_url,
                mime_type=mime_type,
                size_bytes=len(content),
                uploaded_by=uploaded_by,
            )
            await self.attachment_repo.create(attachment)
        except (ValidationError, SQLAlchemyError):
            logger.exception("Error occurred while saving attachment in database")
            await self.s3_client.delete(object_key)
        else:
            return attachment
