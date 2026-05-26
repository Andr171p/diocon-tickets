from typing import TypeVar

from .shared.domain.events import Event
from .tickets.domain.events import TicketCreated

EventT = TypeVar("EventT", bound=Event)

# Маппинг доменных событий к топикам в которых они будут обработаны (очереди)
EVENT_TOPIC_MAP: dict[type[EventT], str] = {
    TicketCreated: "tickets.create"
}
