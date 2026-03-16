import asyncio
import logging

import anyio

from src.s3 import S3Client
from src.settings import settings


async def main() -> None:
    bucket_name = "diocon-avatars-public"
    client = S3Client(
        access_key=settings.minio.access_key_id,
        secret_key=settings.minio.secret_access_key,
        endpoint_url=settings.minio.endpoint_url,
        bucket_name=bucket_name,
    )
    # await client.make_bucket_public()
    file_name = "photo_2026-03-15_12-44-39.jpg"
    file_data = await anyio.Path(file_name).read_bytes()
    await client.upload(file_data, key=file_name)
    print(client.get_public_url(file_name))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
