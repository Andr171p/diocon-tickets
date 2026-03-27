from typing import Annotated

from fastapi import Depends

from ..core.settings import settings
from .domain.ports import Storage
from .infra.s3 import S3Storage
from .services import AttachmentService


def get_storage() -> Storage:
    return S3Storage(
        access_key=settings.minio.access_key_id,
        secret_key=settings.minio.secret_access_key,
        endpoint_url=settings.minio.endpoint_url,
        bucket_name="test-data"
    )


def get_attachment_service(
        storage: Storage = Depends(get_storage),
) -> AttachmentService:
    return AttachmentService(storage=storage)


AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
