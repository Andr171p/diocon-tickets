from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from typing_extensions import Doc

from src.media.domain.entities import Attachment
from src.shared.domain.entities import AggregateRoot
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.domain.vo import Priority, Tag
from src.shared.utils.time import current_datetime

from .events import (
    TicketApprovalSubmitted,
    TicketApproved,
    TicketArchived,
    TicketAssigned,
    TicketCanceled,
    TicketClosed,
    TicketCreated,
    TicketEdited,
    TicketPaused,
    TicketPriorityChanged,
    TicketRejected,
    TicketReopened,
    TicketResolved,
    TicketStatusChanged,
)
from .fsm import transition
from .vo import TicketNumber, TicketStatus, TicketType


@dataclass(kw_only=True)
class Ticket(AggregateRoot):
    """
    Заявка - запрос на услугу от пользователя.
    """

    project_id: UUID | None = None
    counterparty_id: UUID | None = None
    product_id: UUID | None = None

    created_by: Annotated[UUID, Doc("Фактический создатель заявки")]
    approved_by: Annotated[UUID | None, Doc("Тот, кто согласовал работы")] = None
    resolved_by: Annotated[UUID | None, Doc("Тот, кто решил тикет")] = None
    closed_by: Annotated[UUID | None, Doc("Пользователь, закрывший тикет")] = None

    reporter_id: Annotated[UUID, Doc("Инициатор/автор проблемы (тот кто пожаловался)")]
    assignee_id: Annotated[UUID | None, Doc("Исполнитель")] = None

    number: TicketNumber
    title: str
    description: str
    type: TicketType
    status: TicketStatus
    priority: Priority

    approved_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    tags: list[Tag] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    def change_status(self, new_status: TicketStatus, changed_by: UUID) -> None:
        if self.status == new_status:
            return

        old_status = self.status
        self.status = new_status
        self.updated_at = current_datetime()

        self.register_event(
            TicketStatusChanged(
                ticket_id=self.id,
                number=self.number,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )

    @classmethod
    def create(
        cls,
        number: TicketNumber,
        reporter_id: UUID,
        created_by: UUID,
        title: str,
        description: str,
        ticket_type: TicketType = TicketType.SERVICE_REQUEST,
        priority: Priority = Priority.MEDIUM,
        project_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        product_id: UUID | None = None,
        tags: list[Tag] | None = None,
    ) -> Self:
        if not title.strip() or not description.strip():
            raise ValueError("Ticket title or description cannot be empty string")

        ticket = cls(
            created_by=created_by,
            reporter_id=reporter_id,
            number=number,
            title=title,
            description=description,
            type=ticket_type,
            priority=priority,
            status=TicketStatus.NEW,
            project_id=project_id,
            counterparty_id=counterparty_id,
            product_id=product_id,
            tags=[] if tags is None else tags,
        )
        ticket.register_event(
            TicketCreated(
                ticket_id=ticket.id,
                title=title,
                number=number,
                created_by=created_by,
                reporter_id=reporter_id,
                priority=priority,
                counterparty_id=counterparty_id,
            )
        )
        return ticket

    @transition(
        TicketStatus.NEW,
        TicketStatus.PENDING_APPROVAL,
        TicketStatus.OPEN,
        TicketStatus.REOPENED,
    )
    def edit(
        self,
        actor_id,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        tags: list[Tag] | None = None,
    ) -> None:
        """Отредактировать информацию и тикете."""

        changed = False
        changes = {}

        if title is not None and title.strip() and title.strip() != self.title:
            old_title = self.title
            self.title = title.strip()

            changes["title"] = [old_title, self.title]
            changed = True

        if description is not None and description.strip() != self.description:
            old_description = self.description
            self.description = description.strip()

            changes["description"] = [old_description, self.description]
            changed = True

        if priority is not None and priority != self.priority:
            old_priority = self.priority
            self.priority = priority

            changes["priority"] = [old_priority.value, self.priority.value]
            changed = True

            self.register_event(
                TicketPriorityChanged(
                    ticket_id=self.id,
                    number=self.number,
                    changed_by=actor_id,
                    old_priority=old_priority,
                    new_priority=self.priority,
                )
            )

        if tags is not None and set(tags) != set(self.tags):
            old_tags = ", ".join([tag.name for tag in self.tags])
            self.tags = tags[:]

            changes["tags"] = [old_tags, ", ".join([tag.name for tag in self.tags])]
            changed = True

        if changed:
            self.updated_at = current_datetime()

            self.register_event(
                TicketEdited(
                    ticket_id=self.id,
                    number=self.number,
                    changes=changes,
                    edited_by=actor_id,
                )
            )

    def archive(self, archived_by: UUID) -> None:
        """Архивировать тикет (мягкое удаление)."""

        if self.is_deleted:
            return

        self.deleted_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            TicketArchived(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                archived_by=archived_by,
            )
        )

    @transition(TicketStatus.NEW, to=TicketStatus.PENDING_APPROVAL)
    def submit_for_approval(self, actor_id: UUID) -> None:
        """
        Запросить согласование работ.
        Бизнесово клиент запрашивает у админа контрагента.
        """

        self.register_event(
            TicketApprovalSubmitted(
                ticket_id=self.id,
                number=self.number,
                submitted_by=actor_id,
                counterparty_id=self.counterparty_id,
            )
        )

    @transition(TicketStatus.PENDING_APPROVAL, to=TicketStatus.OPEN)
    def approve(self, actor_id: UUID) -> None:
        """
        Согласовать тикет.
        После этого действия заявка считается открытой.
        """

        self.approved_by = actor_id
        self.approved_at = current_datetime()

        self.register_event(
            TicketApproved(
                ticket_id=self.id,
                number=self.number,
                approved_by=actor_id,
                counterparty_id=self.counterparty_id,
            )
        )

    @transition(
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING,
        TicketStatus.REOPENED,
    )
    def assign(self, assignee_id: UUID, actor_id: UUID) -> None:
        """Назначить исполнителя на тикет."""

        if self.assignee_id == assignee_id:
            return

        old_assignee = self.assignee_id
        self.assignee_id = assignee_id

        self.register_event(
            TicketAssigned(
                ticket_id=self.id,
                number=self.number,
                title=self.title,
                assigned_by=actor_id,
                assignee_id=assignee_id,
                old_assignee=old_assignee,
            )
        )

    @transition(
        TicketStatus.OPEN,
        TicketStatus.PAUSED,
        TicketStatus.WAITING,
        TicketStatus.REOPENED,
        to=TicketStatus.IN_PROGRESS,
    )
    def start_progress(self, actor_id: UUID) -> None:
        """Начать работу над заявкой."""

        if self.assignee_id is None:
            raise InvariantViolationError("Assignee required to start progress.")

        if self.assignee_id != actor_id:
            raise InvariantViolationError("Only assignee can start progress.")

    @transition(TicketStatus.IN_PROGRESS, to=TicketStatus.PAUSED)
    def pause(self, reason: str, actor_id: UUID) -> None:
        """
        Поставить выполнение заявки на паузу.
        Важным моментом является указание причины.
        """

        if not reason.strip():
            raise ValueError("Ticket pause reason cannot be empty string")

        self.register_event(
            TicketPaused(
                ticket_id=self.id,
                number=self.number,
                reason=reason,
                paused_by=actor_id,
            ),
        )

    @transition(TicketStatus.IN_PROGRESS, TicketStatus.WAITING, to=TicketStatus.RESOLVED)
    def resolve(self, actor_id: UUID) -> None:
        self.resolved_by = actor_id
        self.resolved_at = current_datetime()

        self.register_event(
            TicketResolved(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                resolved_by=actor_id,
            ),
        )

    @transition(TicketStatus.RESOLVED, TicketStatus.CLOSED, to=TicketStatus.REOPENED)
    def reopen(self, actor_id: UUID) -> None:
        """
        Переоткрыть тикет.
        Сценарий использования: по решённой заявке возникла ошибка.
        """

        self.resolved_by = None
        self.resolved_at = None

        self.closed_by = None
        self.closed_at = None

        self.register_event(
            TicketReopened(
                ticket_id=self.id,
                number=self.number,
                assignee_id=self.assignee_id,
                reopened_by=actor_id,
            )
        )

    @transition(
        TicketStatus.NEW,
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PAUSED,
        TicketStatus.WAITING,
        to=TicketStatus.CANCELED,
    )
    def cancel(self, actor_id: UUID) -> None:
        self.register_event(
            TicketCanceled(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                assignee_id=self.assignee_id,
                canceled_by=actor_id,
            )
        )

    @transition(TicketStatus.PENDING_APPROVAL, to=TicketStatus.REJECTED)
    def reject(self, actor_id: UUID) -> None:
        """Отклонить тикет на этапе согласования."""

        self.register_event(
            TicketRejected(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                rejected_by=actor_id,
            )
        )

    @transition(TicketStatus.RESOLVED, to=TicketStatus.CLOSED)
    def close(self, actor_id: UUID) -> None:
        """
        Закрыть тикет (заявка считается решённой после успешного решения
        и согласования с клиентом).
        """

        self.closed_by = actor_id
        self.closed_at = current_datetime()

        self.register_event(
            TicketClosed(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                closed_by=actor_id,
            ),
        )
