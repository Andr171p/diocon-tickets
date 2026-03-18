import logging
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import NotFoundError
from ..db.repos import UserRepository
from ..schemas import UserResponse
from ..settings import ALLOWED_IMAGES_EXTENSIONS, MAX_AVATAR_SIZE_BYTES
from .attachment import AttachmentService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession, attachment_service: AttachmentService) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.attachment_service = attachment_service

    async def upload_avatar(self, user_id: UUID, file: UploadFile) -> UserResponse:
        """Загрузка аватара для учётной записи пользователя и возвращает публичный URL"""

        user = await self.user_repo.read(user_id)
        if user is None:
            raise NotFoundError(f"User with ID {user_id} not found")

        if file.filename.rsplit(".", maxsplit=1)[-1] not in ALLOWED_IMAGES_EXTENSIONS:
            raise ValueError("Unsupported image type!")

        attachment = await self.attachment_service.upload_file(
            entity_type="user_avatar",
            entity_id=user.id,
            file=file,
            uploaded_by=user.id,
            is_public=True,
            max_size_bytes=MAX_AVATAR_SIZE_BYTES,
        )
        user = await self.user_repo.update(user.id, avatar_url=attachment.public_url)
        await self.session.commit()
        return UserResponse.model_validate(user)
