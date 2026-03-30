import io
from uuid import uuid4

import httpx
import pytest
from fastapi import status

from src.media.domain.entities import Attachment
from src.shared.utils.time import current_datetime


@pytest.mark.asyncio(loop_scope="session")
async def test_full_upload_and_preview_flow(
        session,
        s3_storage,
        attachment_repo,
        attachment_service,
        imgproxy_service,
):
    owner_id = uuid4()
    storage_key = f"test/{owner_id}/avatar.jpg"
    content_type = "image/jpeg"

    # 1. Загрузка тестового изображения в S3
    test_image = b"fake image content"
    await s3_storage.upload(io.BytesIO(test_image), storage_key, content_type=content_type)

    # 2. Создание attachment
    attachment = Attachment(
        original_filename="avatar.jpg",
        mime_type=content_type,
        size_bytes=len(test_image),
        storage_key=storage_key,
        owner_type="user",
        owner_id=owner_id,
        is_public=True,
        uploaded_at=current_datetime(),
        uploaded_by_id=uuid4(),
    )
    await attachment_repo.create(attachment)
    await session.commit()

    # 3. Проверка успешной загрузки файла
    file_info = await s3_storage.get_file_info(storage_key)

    assert file_info.get("size") is not None
    assert file_info["size"] == len(test_image)

    # 4. Проверка генерации preview через imgproxy
    preview_url = imgproxy_service.preview(storage_key)
    print(preview_url)

    # 5. Проверка preview URL на валидность и доступность
    async with httpx.AsyncClient() as client:
        response = await client.get(preview_url, follow_redirects=True)
        print(f"Response Body: {response.text[:1000]}")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("Content-Type") in {"image/webp", "image/jpeg", "image/png"}

    # 6. Проверка записи в БД
    existing_attachment = await attachment_repo.read(attachment.id)

    assert existing_attachment is not None
    assert existing_attachment.storage_key == storage_key
