import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from src.shared.domain.events import Event
from src.shared.infra.events import EventBus


@pytest.fixture
async def event_bus():
    event_bus = EventBus(max_queue_size=10)
    await event_bus.start()
    yield event_bus
    await event_bus.stop()


# ==================== Вспомогательные классы и функции для тестов ====================


@dataclass(frozen=True, kw_only=True)
class TestEvent(Event):
    value: str


# ========================== Тесты ==========================


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish(event_bus):
    handler = AsyncMock()
    event_bus.subscribe(TestEvent, handler)

    event = TestEvent(value="test_value")
    await event_bus.publish(event)

    await asyncio.sleep(0.05)

    handler.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_publish_all(event_bus):
    handler = AsyncMock()

    event_bus.subscribe(TestEvent, handler)

    events = [
        TestEvent(value="event1"),
        TestEvent(value="event2"),
        TestEvent(value="event3"),
    ]
    excepted_call_count = 3

    await event_bus.publish_all(events)

    await asyncio.sleep(0.05)

    assert handler.call_count == excepted_call_count


@pytest.mark.asyncio
async def test_multiple_handlers_for_same_event(event_bus):
    handler1 = AsyncMock()
    handler2 = AsyncMock()

    event_bus.subscribe(TestEvent, handler1)
    event_bus.subscribe(TestEvent, handler2)

    event = TestEvent(value="multi")
    await event_bus.publish(event)
    await asyncio.sleep(0.05)

    handler1.assert_awaited_once_with(event)
    handler2.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_handler_exception_is_caught_and_logged(event_bus):

    def bad_handler(event: Event):
        raise ValueError("Test error")

    event_bus.subscribe(TestEvent, bad_handler)

    with patch("src.shared.infra.events.logger.exception") as mock_log:
        event = TestEvent(value="error_test")
        await event_bus.publish(event)
        await asyncio.sleep(0.05)

        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_no_handlers_for_event(event_bus):
    with patch("src.shared.infra.events.logger.debug") as mock_log:
        event = TestEvent(value="no_handler")
        await event_bus.publish(event)
        await asyncio.sleep(0.05)

        mock_log.assert_called_with("No handlers registered for event: %s", "TestEvent")
