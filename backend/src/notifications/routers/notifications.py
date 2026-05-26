from typing import Annotated

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.sse import EventSourceResponse
from faststream.rabbit import RabbitQueue, RabbitRouter

from ...iam.dependencies import CurrentUserDep
from ...shared.dependencies import PaginationDep, sse_manager
from ...shared.schemas import Page, Pagination
from ..dependencies import NotificationRepoDep, NotificationServiceDep
from ..mappers import map_notification_to_response
from ..schemas import NotificationResponse, UnreadCountOut

logger = logging.getLogger(__name__)

mq_router = RabbitRouter()

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[NotificationResponse],
    summary="Получение моих уведомлений",
)
async def get_my_notifications(
        current_user: CurrentUserDep,
        repository: NotificationRepoDep,
        pagination: PaginationDep,
        unread_only: Annotated[
            bool, Query(..., description="Учитывать только непрочитанные")
        ] = False,
) -> Page[NotificationResponse]:
    page = await repository.get_by_user(current_user.user_id, pagination, unread_only)
    return page.to_response(map_notification_to_response)


@router.get(
    path="/unread-count",
    status_code=status.HTTP_200_OK,
    response_model=UnreadCountOut,
    summary="Получение количества непрочитанных уведомлений",
)
async def get_unread_count(
        current_user: CurrentUserDep, repository: NotificationRepoDep
) -> UnreadCountOut:
    return {"unread_count": await repository.get_unread_count(current_user.user_id)}


@router.patch(
    path="/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    response_model=NotificationResponse,
    summary="Пометить уведомление как прочитанное",
)
async def mark_as_read(
        notification_id: UUID,
        current_user: CurrentUserDep,
        service: NotificationServiceDep,
) -> NotificationResponse:
    return await service.mark_as_read(notification_id, read_by=current_user.user_id)


@mq_router.subscriber(
    queue=RabbitQueue("notifications.sse", auto_delete=True),
    description="Отправка уведомления в локальную очередь"
)
async def handle_notification(message: NotificationResponse):
    await sse_manager.send_to_user(message.user_id, message.model_dump())


@router.get(
    path="/stream",
    response_class=EventSourceResponse,
    summary="Соединение для отправки уведомлений",
)
async def notification_stream(
        request: Request, current_user: CurrentUserDep, repository: NotificationRepoDep
):
    # Инициализация подключения
    queue: asyncio.Queue[NotificationResponse] = asyncio.Queue(maxsize=10)
    await sse_manager.connect(current_user.user_id, queue)

    async def event_generator():

        try:
            # 1. Отправка последних непрочитанных уведомлений при подключении
            unread_notifications = await repository.get_by_user(
                user_id=current_user.user_id,
                pagination=Pagination(page=1, size=50),
                unread_only=True,
            )
            for notification in unread_notifications.items:
                payload = {
                    "type": "notification",
                    "notification": map_notification_to_response(notification).model_dump_json(),
                }
                yield {"data": payload}

            # 2. Основной цикл прослушивания очереди
            while True:
                if await request.is_disconnected():
                    logger.debug("Client disconnected (SSE)")
                    break

                try:
                    # Ожидание сообщения из очереди
                    message = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield {"data": message.model_dump_json()}
                except TimeoutError:
                    # Heartbeat - для удержания соединения
                    yield {"comment": "ping"}

        finally:
            # Всегда отключаем пользователя при завершении
            await sse_manager.disconnect(current_user.user_id, queue)

    return EventSourceResponse(event_generator())
