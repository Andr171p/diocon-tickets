from src.activity_logs.recorder import ActivityLogRecorder

from .domain.entities import Entity
from .domain.events import EventPublisher
from .domain.repos import UnitOfWork


async def commit[EntityT: Entity](
        uow: UnitOfWork,
        *aggregates: EntityT,
        event_publisher: EventPublisher,
        recorder: ActivityLogRecorder | None = None,
) -> None:
    events = []
    for aggregate in aggregates:
        events.extend(aggregate.collect_events())

    if recorder is not None:
        await recorder.record_all(events)

    await uow.commit()

    await event_publisher.publish_all(events)
