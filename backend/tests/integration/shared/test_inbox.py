from uuid import uuid4

import pytest
from sqlalchemy import select

from src.event_config import EVENT_TOPIC_MAP
from src.tickets.domain.events import TicketCreated
from src.shared.infra.inbox import InboxMessage, InboxRepository, MessageStatus

@pytest.fixture
def inbox_repo(session):
    return InboxRepository(session)


@pytest.mark.asyncio
async def test_add_returns_true_for_new_message(session, inbox_repo):
    """
    Проверяем сохранение нового inbox-сообщения: repository должен добавить
    событие в БД и вернуть True.
    Данные: уникальные message_id/event_type и payload события.
    """

    message_id = f"msg-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]
    payload = {
        "ticket_id": str(uuid4()),
        "title": "Test ticket"
    }

    created = await inbox_repo.add(message_id, event_type, payload)
    await session.commit()

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.message_id == message_id,
            InboxMessage.event_type == event_type,
        )
    )
    message = result.scalar_one()

    assert created is True
    assert message.message_id == message_id
    assert message.event_type == event_type
    assert message.payload == payload
    assert message.status == MessageStatus.PENDING


@pytest.mark.asyncio
async def test_add_returns_false_for_duplicate_message(session, inbox_repo):
    """
    Проверяем защиту от дублей: если message_id/event_type уже есть,
    repository должен вернуть False и не создать вторую запись.
    Данные: два add() с одинаковыми message_id и event_type.
    """

    message_id = f"msg-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]
    payload = {
        "ticket_id": str(uuid4()),
        "title": "Test ticket",
    }

    first_created = await inbox_repo.add(message_id, event_type, payload)
    second_created = await inbox_repo.add(message_id, event_type, payload)
    await session.commit()

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.message_id == message_id,
            InboxMessage.event_type == event_type,
        )
    )
    messages = result.scalars().all()

    assert first_created is True
    assert second_created is False
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_get_pending_returns_only_pending_messages(session, inbox_repo):
    """
    Проверяем получение pending-сообщений: get_pending должен вернуть только
    сообщения со статусом PENDING.
    Данные: одно pending-сообщение, одно processed и одно failed.
    """

    pending_message_id = f"pending-{uuid4()}"
    processed_message_id = f"processed-{uuid4()}"
    failed_message_id = f"failed-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]

    await inbox_repo.add(
        pending_message_id,
        event_type,
        {"ticket_id": str(uuid4()), "title": "Pending ticket"},
    )
    await inbox_repo.add(
        processed_message_id,
        event_type,
        {"ticket_id": str(uuid4()), "title": "Processed ticket"},
    )
    await inbox_repo.add(
        failed_message_id,
        event_type,
        {"ticket_id": str(uuid4()), "title": "Failed ticket"},
    )

    await inbox_repo.mark_processed(processed_message_id, event_type)
    await inbox_repo.mark_failed(failed_message_id, event_type, "handler failed")
    await session.commit()

    messages = await inbox_repo.get_pending()

    message_ids = {message.message_id for message in messages}

    assert pending_message_id in message_ids
    assert processed_message_id not in message_ids
    assert failed_message_id not in message_ids


@pytest.mark.asyncio
async def test_get_pending_respects_limit(session, inbox_repo):
    """
    Проверяем ограничение количества pending-сообщений: get_pending(limit)
    должен вернуть не больше указанного количества записей.
    Данные: три pending-сообщения и limit=2.
    """

    event_type = EVENT_TOPIC_MAP[TicketCreated]

    await inbox_repo.add(
        f"pending-{uuid4()}",
        event_type,
        {"ticket_id": str(uuid4()), "title": "First ticket"},
    )
    await inbox_repo.add(
        f"pending-{uuid4()}",
        event_type,
        {"ticket_id": str(uuid4()), "title": "Second ticket"},
    )
    await inbox_repo.add(
        f"pending-{uuid4()}",
        event_type,
        {"ticket_id": str(uuid4()), "title": "Third ticket"},
    )
    await session.commit()

    messages = await inbox_repo.get_pending(limit=2)

    assert len(messages) == 2


@pytest.mark.asyncio
async def test_mark_processed_updates_status_and_processed_at(session, inbox_repo):
    """
    Проверяем успешную обработку inbox-сообщения: mark_processed должен
    изменить статус на PROCESSED, заполнить processed_at и очистить error_message.
    Данные: новое pending-сообщение.
    """

    message_id = f"msg-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]
    payload = {
        "ticket_id": str(uuid4()),
        "title": "Test ticket",
    }

    await inbox_repo.add(message_id, event_type, payload)
    await inbox_repo.mark_processed(message_id, event_type)
    await session.commit()

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.message_id == message_id,
            InboxMessage.event_type == event_type,
        )
    )
    message = result.scalar_one()

    assert message.status == MessageStatus.PROCESSED
    assert message.processed_at is not None
    assert message.error_message is None


@pytest.mark.asyncio
async def test_mark_failed_updates_status_and_error_message(session, inbox_repo):
    """
    Проверяем ошибочную обработку inbox-сообщения: mark_failed должен
    изменить статус на FAILED, сохранить текст ошибки и заполнить processed_at.
    Данные: новое pending-сообщение и текст ошибки.
    """

    message_id = f"msg-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]
    payload = {
        "ticket_id": str(uuid4()),
        "title": "Test ticket",
    }
    error_message = "handler failed"

    await inbox_repo.add(message_id, event_type, payload)
    await inbox_repo.mark_failed(message_id, event_type, error_message)
    await session.commit()

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.message_id == message_id,
            InboxMessage.event_type == event_type,
        )
    )
    message = result.scalar_one()

    assert message.status == MessageStatus.FAILED
    assert message.processed_at is not None
    assert message.error_message == error_message


