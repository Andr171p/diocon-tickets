from typing import TypeVar

from .shared.domain.events import Event
from .tickets.domain.events import TicketCreated
from .timetracking.domain.events import WorklogApproved

EventT = TypeVar("EventT", bound=Event)

# Маппинг доменных событий к топикам в которых они будут обработаны (очереди)
EVENT_TOPIC_MAP: dict[type[EventT], str] = {
    TicketCreated: "tickets.create",
    WorklogApproved: "worklogs.approve",
}
