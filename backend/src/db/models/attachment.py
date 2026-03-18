from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AttachmentOrm(Base):
    __tablename__ = "attachments"

    entity_type: Mapped[str]
    entity_id: Mapped[UUID]
    file_name: Mapped[str]
    original_name: Mapped[str]
    object_key: Mapped[str] = mapped_column(unique=True)
    public_url: Mapped[str | None] = mapped_column(nullable=True)
    mime_type: Mapped[str]
    size_bytes: Mapped[int]
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=False)
    is_deleted: Mapped[bool]
