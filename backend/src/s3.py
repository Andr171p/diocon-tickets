import json
import logging
import math
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager

from aiobotocore.session import get_session

logger = logging.getLogger(__name__)


class S3Client:
    def __init__(
            self,
            access_key: str,
            secret_key: str,
            endpoint_url: str,
            bucket_name: str,
    ) -> None:
        self.config = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client(**self.config) as client:
            yield client

    async def make_bucket_public(self) -> None:
        """Сделать бакет публичным"""

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                }
            ],
        }
        async with self.get_client() as client:
            await client.put_bucket_policy(Bucket=self.bucket_name, Policy=json.dumps(policy))

    async def upload(self, file_data: bytes, key: str) -> None:
        """Загрузка файла в хранилище"""

        async with self.get_client() as client:
            await client.put_object(Bucket=self.bucket_name, Key=key, Body=file_data)

    async def upload_multipart(self, chunks: AsyncIterable[bytes], key: str) -> None:
        """Загрузка объекта в хранилище по частям"""

        upload_id = None
        parts = []
        async with self.get_client() as client:
            part_number = 1
            async for chunk in chunks:
                if upload_id is None:
                    response = await client.create_multipart_upload(
                        Bucket=self.bucket_name, Key=key
                    )
                    upload_id = response["UploadId"]
                    logger.info("Initiate multipart uploading, key - `%s`", key)
                response = await client.upload_part(
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=chunk,
                )
                parts.append({"PartNumber": part_number, "ETag": response["ETag"]})
                logger.info("Successful upload %s part for key `%s`", part_number, key)
                part_number += 1
            await client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.info("Multipart upload completed %s parts for key `%s`", len(parts), key)

    async def download(self, key: str) -> None:
        """Скачивание файла из хранилища"""

        async with self.get_client() as client:
            response = await client.get_object(Bucket=self.bucket_name, Key=key)
            return await response["Body"].read()

    async def download_multipart(
            self, key: str, chunk_size: int = 1024 * 1024
    ) -> AsyncIterable[bytes]:
        async with self.get_client() as client:
            head = await client.head_object(Bucket=self.bucket_name, Key=key)
            size = head["ContentLength"]
            part_numbers = math.ceil(size / chunk_size)
            logger.info(
                "Start multipart downloading for key `%s`, size %s mb, total parts %s",
                key,
                round(size / (1024 * 1024), 2),
                part_numbers,
            )
            for part_number in range(part_numbers):
                start = part_number * chunk_size
                end = min((part_number + 1) * chunk_size - 1, size - 1)
                logger.info(
                    "Downloading `%s` part %s : bytes %s-%s", key, part_number, start, end
                )
                response = await client.get_object(
                    Bucket=self.bucket_name, Key=key, Range=f"bytes={start}-{end}"
                )
                yield await response["Body"].read()

    async def delete(self, key: str) -> None:
        """Удаление объекта из хранилища"""

        async with self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=key)

    async def create_presigned_url(self, key: str, expires_in: int = 60 * 60) -> str:
        """Создание пред-подписанного временного URL для скачивания объекта"""

        async with self.get_client() as client:
            return await client.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket_name, "Key": key}, ExpiresIn=expires_in
            )

    def get_public_url(self, key: str) -> str:
        """Получение публичного URL объекта"""

        endpoint = self.config["endpoint_url"].rstrip("/")
        return f"{endpoint}/{self.bucket_name}/{key.lstrip('/')}"
