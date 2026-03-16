from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .db.base import session_factory
from .db.repos import CounterpartyRepository
from .services.notification import NotificationService


async def get_db() -> AsyncSession:
    async with session_factory() as session:
        yield session


def get_counterparty_repo(session: AsyncSession = Depends(get_db)) -> CounterpartyRepository:
    return CounterpartyRepository(session)


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)
