from typing import Annotated

from fastapi import Depends

from ..core.settings import settings
from ..shared.dependencies import SessionDep
from .domain.ports import AttachmentRepository, Storage
from .infra.repo import SqlAttachmentRepository
from .infra.s3 import S3Storage
from .services import AttachmentService


def get_storage() -> Storage:
    return S3Storage(
        access_key=settings.minio.access_key_id,
        secret_key=settings.minio.secret_access_key,
        endpoint_url=settings.minio.endpoint_url,
        bucket_name="test-data"
    )


def get_attachment_repo(session: SessionDep) -> AttachmentRepository:
    return SqlAttachmentRepository(session)


def get_attachment_service(
        session: SessionDep,
        storage: Storage = Depends(get_storage),
        repository: AttachmentRepository = Depends(get_attachment_repo),
) -> AttachmentService:
    return AttachmentService(session=session, storage=storage, repository=repository)


AttachmentRepoDep = Annotated[AttachmentRepository, Depends(get_attachment_repo)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
