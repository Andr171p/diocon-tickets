from src.projects.domain.vo import ProjectKey
from src.shared.utils.time import current_datetime

from .dtos import TicketDraft
from .entities import Ticket
from .vo import TicketNumber, TicketPrefix


def resolve_ticket_prefix(
        project_key: ProjectKey | None = None, counterparty_name: str | None = None,
) -> TicketPrefix:
    """Определяет префикс для номера заявки."""

    if project_key is not None:
        return TicketPrefix.from_project(project_key)

    if counterparty_name is not None:
        return TicketPrefix.from_counterparty(counterparty_name)

    return TicketPrefix.internal()


def generate_ticket_number(prefix: TicketPrefix, sequence: int) -> TicketNumber:
    """Генерирует уникальный номер заявки на основе длины последовательности и префикса."""

    year = current_datetime().year % 100

    return TicketNumber(prefix=prefix, year=year, sequence=sequence)


def create_ticket(draft: TicketDraft, sequence: int) -> Ticket:
    """Создаёт заявку и определяет её номер."""

    project_key = draft.project.key if draft.project else None
    counterparty_name = draft.counterparty.name if draft.counterparty else None

    prefix = resolve_ticket_prefix(project_key=project_key, counterparty_name=counterparty_name)
    number = generate_ticket_number(prefix=prefix, sequence=sequence)

    project_id = draft.project.id if draft.project else None
    counterparty_id = draft.counterparty.id if draft.counterparty else None

    return Ticket.create(
        number=number,
        title=draft.title,
        description=draft.description,
        created_by=draft.created_by,
        reporter_id=draft.reporter_id,
        ticket_type=draft.type,
        priority=draft.priority,
        tags=draft.tags,
        project_id=project_id,
        counterparty_id=counterparty_id,
        product_id=draft.product_id,
    )
