import logging

from src.core.entities import User, UserRole
from src.db.base import session_factory
from src.db.repos import UserRepository
from src.s3 import get_private_s3_client, get_public_s3_client
from src.settings import settings
from src.utils.secutiry import hash_password

logger = logging.getLogger(__name__)


async def create_first_admin() -> None:
    """Создание системного администратора"""

    async with session_factory() as session:
        user_repo = UserRepository(session)
        exists = await user_repo.get_by_email(settings.admin.email)
        if exists:
            logger.warning("Admin already exists")
            return
        admin = User(
            email=settings.admin.email,
            username="admin",
            full_name="Иванов Иван Иванович",
            role=UserRole.ADMIN,
            password_hash=hash_password(settings.admin.password),
            is_active=True,
        )
        await user_repo.create(admin)
        await session.commit()
        logger.info("First admin created successfully")


async def init_s3_storage() -> None:
    """Создание S3 бакетов"""

    # 1. Инициализация приватного S3 клиента
    private_s3_client = get_private_s3_client()
    await private_s3_client.create_bucket()

    # 2. Инициализация публичного S3 клиента
    public_s3_client = get_public_s3_client()
    await public_s3_client.create_bucket()
    await public_s3_client.make_bucket_public()

    logger.info("S3 storage initialized successfully")
