from dataclasses import dataclass
from uuid import UUID

from src.crm.domain.entities import Counterparty
from src.projects.domain.entities import Project
from src.shared.domain.dtos import TimeRangeFilters
from src.shared.domain.vo import Priority, Tag

from .vo import TicketNumber, TicketStatus, TicketType


@dataclass(frozen=True)
class TicketDraft:
    """Черновик для создания заявки."""

    title: str
    description: str

    reporter_id: UUID
    created_by: UUID

    type: TicketType
    priority: Priority
    tags: list[Tag] | None = None

    project: Project | None = None
    counterparty: Counterparty | None = None
    product_id: UUID | None = None


@dataclass(frozen=True)
class ActorsFilters:
    """Фильтры по участникам процесса."""

    assignee_id: UUID | None = None
    reporter_id: UUID | None = None
    creator_id: UUID | None = None


@dataclass(frozen=True)
class TicketFilters:
    """Все возможные фильтры для тикетов."""

    search_query: str | None = None
    tags: list[str] | None = None

    counterparty_id: UUID | None = None
    project_ids: set[UUID] | None = None

    statuses: list[TicketStatus] | None = None
    priorities: Priority | None = None
    type: TicketType | None = None

    actors: ActorsFilters | None = None
    time_range: TimeRangeFilters | None = None
