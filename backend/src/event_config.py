from typing import TypeVar

from src.iam.domain.events import UserInvited
from src.shared.domain.events import Event
from src.tickets.domain.events import TicketCreated
from src.timetracking.domain.events import WorklogApproved

EventT = TypeVar("EventT", bound=Event)

# Маппинг доменных событий к топикам в которых они будут обработаны (очереди)
EVENT_TOPIC_MAP: dict[type[EventT], str] = {
    TicketCreated: "tickets.create",
    WorklogApproved: "worklogs.approve",
    UserInvited: "users.invite",
}
