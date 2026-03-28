from .domain.entities import Attachment
from .infra.imgproxy import imgproxy_service
from .schemas import AttachmentResponse


def map_attachment_to_response(attachment: Attachment) -> AttachmentResponse:
    """
    Преобразование доменной модели к API схеме ответа
    (с получением preview URL для изображений).
    """

    preview_url = None
    if attachment.is_image:
        preview_url = imgproxy_service.preview(attachment.storage_key)

    return AttachmentResponse(
        id=attachment.id,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        storage_key=attachment.storage_key,
        owner_type=attachment.owner_type,
        owner_id=attachment.owner_id,
        uploaded_at=attachment.uploaded_at,
        uploaded_by_id=attachment.uploaded_by_id,
        preview_url=preview_url,
    )
