import os

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.core.generic import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import PortWaitStrategy
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer

from src.core.database import Base
from src.media.infra.imgproxy import ImgProxyService
from src.media.infra.repo import SqlAttachmentRepository
from src.media.infra.s3 import S3Storage
from src.media.services import AttachmentService


@pytest.fixture(scope="session")
def minio_secret_key():
    return "minioadmin123"


@pytest.fixture(scope="session")
def imgproxy_key():
    return "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@pytest.fixture(scope="session")
def imgproxy_salt():
    return "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"


@pytest.fixture(scope="session")
def network():
    with Network() as network:
        yield network


@pytest.fixture(scope="session")
def minio_container(minio_secret_key, network):
    minio_container = (
        MinioContainer(
            image="quay.io/minio/minio", access_key="minioadmin", secret_key=minio_secret_key,
        )
        .with_network(network)
        .waiting_for(PortWaitStrategy(port=9000))
        .with_env("MINIO_ROOT_USER", "minioadmin")
        .with_env("MINIO_ROOT_PASSWORD", minio_secret_key)
        .with_bind_ports(9000, 9000)
    )
    with minio_container as minio:
        client = minio.get_client()
        if not client.bucket_exists("test-bucket"):
            client.make_bucket("test-bucket")
            public_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::test-bucket/*"],
                    }
                ],
            }
            client.set_bucket_policy("test-bucket", json.dumps(public_policy))
        yield minio


@pytest.fixture(scope="session")
def imgproxy_container(
        minio_container, minio_secret_key, imgproxy_key, imgproxy_salt, network
):
    container = (
        DockerContainer("ghcr.io/imgproxy/imgproxy:latest")
        .with_network(network)
        .with_env("IMGPROXY_USE_S3", "true")
        .with_env(
            "IMGPROXY_S3_ENDPOINT",
            f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        )
        .with_env("IMGPROXY_S3_REGION", "us-east-1")
        .with_env("IMGPROXY_S3_ENDPOINT_USE_PATH_STYLE", "true")
        .with_env("IMGPROXY_S3_FORCE_PATH_STYLE", "true")
        .with_env("AWS_ACCESS_KEY_ID", "minioadmin")
        .with_env("AWS_SECRET_ACCESS_KEY", minio_secret_key)
        .with_env("IMGPROXY_LOG_LEVEL", "debug")
        # .with_env("IMGPROXY_KEY", imgproxy_key)
        # .with_env("IMGPROXY_SALT", imgproxy_salt)
        .with_bind_ports(8080, 8081)
    )

    with container:
        yield container


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(image="postgres:16.9", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
async def engine(postgres_container):
    engine = create_async_engine(
        url=postgres_container.get_connection_url(), echo=True, pool_pre_ping=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def session(engine):
    sessionmaker = async_sessionmaker(
        engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )
    async with sessionmaker() as session:
        yield session


@pytest.fixture(scope="session")
def s3_storage(minio_container, minio_secret_key):
    return S3Storage(
        endpoint_url=f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        access_key="minioadmin",
        secret_key=minio_secret_key,
        bucket_name="test-bucket",
    )


@pytest.fixture(scope="session")
def attachment_repo(session):
    return SqlAttachmentRepository(session)


@pytest.fixture(scope="session")
def imgproxy_service(imgproxy_container, imgproxy_key, imgproxy_salt):
    host = imgproxy_container.get_container_host_ip()
    port = imgproxy_container.get_exposed_port(8080)
    return ImgProxyService(
        base_url=f"http://{host}:{port}",
        bucket_name="test-bucket",
        # key=imgproxy_key,
        # salt=imgproxy_salt,
    )


@pytest.fixture
def attachment_service(session, attachment_repo, s3_storage):
    return AttachmentService(session=session, storage=s3_storage, repository=attachment_repo)
