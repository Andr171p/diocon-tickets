from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from typing_extensions import Doc

from src.media.domain.entities import Attachment
from src.shared.domain.entities import AggregateRoot
from src.shared.domain.exceptions import InvalidStateError
from src.shared.domain.vo import Priority, Tag
from src.shared.utils.time import current_datetime

from ..events import (
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
    TicketReopened,
    TicketResolved,
    TicketStatusChanged,
)
from ..transition_factory import get_transition
from ..vo import (
    TicketAction,
    TicketNumber,
    TicketStatus,
    TicketType,
)


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

    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    tags: list[Tag] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.description.strip():
            raise ValueError("Ticket title or description cannot be empty")

    def _perform(self, action: TicketAction, actor_id: UUID, *args) -> None:
        """Выполняет переход в новое состояние."""

        transition = get_transition(self.status, action)

        if transition is None:
            raise InvalidStateError(
                f"Invalid ticket transition for action - {action.value} "
                f"from status {self.status.value}"
            )

        if transition.handler is not None:
            transition.handler(self, actor_id, *args)

        self.updated_at = current_datetime()

        if not transition.changes_status:
            return

        old_status = self.status
        self.status = transition.to

        self.register_event(
            TicketStatusChanged(
                ticket_id=self.id,
                old_status=old_status,
                new_status=self.status,
                changed_by=actor_id,
            )
        )

    # ====================== Публичное API ======================

    @classmethod
    def create(
        cls,
        number: TicketNumber,
        reporter_id: UUID,
        created_by: UUID,
        title: str,
        description: str | None = None,
        ticket_type: TicketType = TicketType.SERVICE_REQUEST,
        priority: Priority = Priority.MEDIUM,
        project_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        product_id: UUID | None = None,
        tags: list[Tag] | None = None,
    ) -> Self:
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

    def edit(
        self,
        edited_by: UUID,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        tags: list[Tag] | None = None,
    ) -> None:
        """
        Отредактировать информацию и тикете.
        """

        self._perform(TicketAction.EDIT, edited_by)

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
                    changed_by=edited_by,
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
                    edited_by=edited_by,
                )
            )

    def archive(self, archived_by: UUID) -> None:
        """
        Заархивировать тикет (мягкое удаление).
        """

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

    def submit_for_approval(self, submitted_by: UUID) -> None:
        """
        Запросить согласование работ.
        Бизнесово клиент запрашивает у админа контрагента.
        """

        self._perform(TicketAction.SUBMIT_FOR_APPROVAL, submitted_by)

        self.register_event(
            TicketApprovalSubmitted(
                ticket_id=self.id,
                number=self.number,
                request_by=submitted_by,
                counterparty_id=self.counterparty_id,
            )
        )

    def approve(self, approved_by: UUID) -> None:
        """
        Согласовать тикет.
        После этого действия заявка считается открытой.
        """

        self._perform(TicketAction.APPROVE, approved_by)

    def assign(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """
        Назначить исполнителя на тикет.
        """

        self._perform(TicketAction.ASSIGN, assigned_by, assignee_id)

    def start_progress(self, started_by: UUID) -> None:
        """Начать работу над заявкой."""

        self._perform(TicketAction.START_PROGRESS, started_by)

    def pause(self, reason: str, paused_by: UUID) -> None:
        """
        Поставить выполнение заявки на паузу.
        Важным моментом является указание причины.
        """

        self._perform(TicketAction.PAUSE, paused_by)

        self.register_event(
            TicketPaused(
                ticket_id=self.id,
                number=self.number,
                reason=reason,
                paused_by=paused_by,
            )
        )

    def resolve(self, resolved_by: UUID) -> None:
        self._perform(TicketAction.RESOLVE, resolved_by)

        self.register_event(
            TicketResolved(
                ticket_id=self.id,
                number=self.number,
                resolved_by=resolved_by,
            )
        )

    def reopen(self, reopened_by: UUID) -> None:
        """
        Переоткрыть тикет.
        Сценарий использования: по решённой заявке возникла ошибка.
        """

        self._perform(TicketAction.REOPEN, reopened_by)

        self.register_event(
            TicketReopened(
                ticket_id=self.id,
                number=self.number,
                assignee_id=self.assignee_id,
                reopened_by=reopened_by,
            )
        )

    def cancel(self, cancelled_by: UUID) -> None:
        self._perform(TicketAction.CANCEL, cancelled_by)

        self.register_event(
            TicketCanceled(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                assignee_id=self.assignee_id,
                cancelled_by=cancelled_by,
            )
        )

    def reject(self, rejected_by: UUID) -> None:
        """
        Отклонить тикет. Например, клиент может отклонить на этапе согласования.
        """

        self._perform(TicketAction.REJECT, rejected_by)

    def close(self, closed_by: UUID) -> None:
        """
        Закрыть тикет (заявка считается решённой после успешного решения
        и согласования с клиентом).
        """

        self._perform(TicketAction.CLOSE, closed_by)

    # ====================== Внутренние мутации ======================

    def mark_approved(self, approved_by: UUID) -> None:
        self.approved_by = approved_by

        self.register_event(
            TicketApproved(
                ticket_id=self.id,
                number=self.number,
                approved_by=approved_by,
                counterparty_id=self.counterparty_id,
            )
        )

    def apply_assignment(self, assignee_id: UUID | None, assigned_by: UUID) -> None:
        """Устанавливает исполнителя + регистрирует событие."""

        if self.assignee_id == assignee_id:
            return

        old_assignee = self.assignee_id
        self.assignee_id = assignee_id

        self.register_event(
            TicketAssigned(
                ticket_id=self.id,
                number=self.number,
                title=self.title,
                assignee_id=assignee_id,
                assigned_by=assigned_by,
                old_assignee=old_assignee,
            )
        )

    def mark_resolved(self, resolved_by: UUID) -> None:
        """Отметить тикет как решённый."""

        self.resolved_by = resolved_by
        self.resolved_at = current_datetime()

        self.register_event(
            TicketResolved(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                resolved_by=resolved_by,
            )
        )

    def clear_resolution(self) -> None:
        """Отчистить информацию о решении тикета."""

        self.resolved_by = None
        self.resolved_at = None

    def mark_closed(self, closed_by: UUID) -> None:
        """Отметить тикет как закрытый."""

        self.closed_by = closed_by
        self.closed_at = current_datetime()

        self.register_event(
            TicketClosed(
                ticket_id=self.id,
                number=self.number,
                closed_by=closed_by,
            )
        )

    def clear_closing(self) -> None:
        """Сбросить время завершения (просто мутация данных)."""

        self.closed_by = None
        self.closed_at = None
