from uuid import UUID

from src.iam.domain.authz import (
    PermissionResult,
    Subject,
    all_allowed,
    any_allowed,
    require,
)
from src.iam.domain.entities import User
from src.iam.domain.rules import is_admin_user, is_support_user
from src.iam.domain.vo import UserRole
from src.projects.domain.repos import ProjectMemberRepository
from src.projects.domain.vo import MemberRole

from .entities import Ticket


def _is_ticket_reporter(subject: Subject, ticket: Ticket) -> PermissionResult:
    if subject.id != ticket.reporter_id:
        return PermissionResult(False, f"You are not a reporter of this ticket - {ticket.id}")

    return PermissionResult(True)


def _is_ticket_creator(subject: Subject, ticket: Ticket) -> PermissionResult:
    if subject.id != ticket.created_by:
        return PermissionResult(False, f"Yoy are not a creator of this ticket - {ticket.id}")

    return PermissionResult(True)


def _is_ticket_assignee(subject: Subject, ticket: Ticket) -> PermissionResult:
    if subject.id != ticket.assignee_id:
        return PermissionResult(False, f"Yoy are not a assignee of this ticket - {ticket.id}")

    return PermissionResult(True)


def _is_belong_to_counterparty(
        subject: Subject, counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Относится ли пользователь к контрагенту."""

    if subject.counterparty_id != counterparty_id:
        return PermissionResult(False, "Customers can only work in their counterparty")

    return PermissionResult(True)


def _can_close_ticket_as_customer(subject: Subject, ticket: Ticket) -> PermissionResult:
    """Может ли клиент закрывать заявку."""

    customer_permission = all_allowed(
        require(subject.has_role(UserRole.CUSTOMER), "CUSTOMER required"),
        _is_ticket_reporter(subject, ticket)
    )

    customer_admin_permission = all_allowed(
        require(subject.has_role(UserRole.CUSTOMER_ADMIN), "CUSTOMER_ADMIN required"),
        _is_belong_to_counterparty(subject, ticket.counterparty_id),
    )

    return any_allowed(customer_permission, customer_admin_permission)


def _can_close_ticket_as_support(subject: Subject, ticket: Ticket) -> PermissionResult:
    """Может ли сотрудник поддержки закрыть заявку."""

    support_agent_permission = all_allowed(
        require(subject.has_role(UserRole.SUPPORT_AGENT), "SUPPORT_AGENT required"),
        _is_ticket_assignee(subject, ticket),
    )

    return any_allowed(
        support_agent_permission,
        require(
            subject.has_any_role(UserRole.SUPPORT_MANAGER, UserRole.ADMIN),
            "SUPPORT_MANAGER or ADMIN required",
        ),
    )


class TicketAuthZService:
    def __init__(self, member_repo: ProjectMemberRepository) -> None:
        self.member_repo = member_repo

    async def can_create_ticket(
            self,
            subject: Subject,
            counterparty_id: UUID | None = None,
            project_id: UUID | None = None,
    ) -> PermissionResult:
        rules = [is_admin_user(subject), _is_belong_to_counterparty(subject, counterparty_id)]

        if project_id:
            member = await self.member_repo.find(project_id, subject.id)
            rules.append(
                require(member is not None, f"You does not exists in project - {project_id}")
            )

        return any_allowed(*rules)

    async def can_access_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            require(subject.has_any_role(*UserRole.staff_roles()), "Require staff role"),
            _is_ticket_reporter(subject, ticket),
            _is_ticket_reporter(subject, ticket),
        ]

        customer_admin_rule = all_allowed(
            require(
                subject.has_role(UserRole.CUSTOMER_ADMIN), "Require CUSTOMER_ADMIN role"
            ),
            _is_belong_to_counterparty(subject, ticket.counterparty_id),
        )
        rules.append(customer_admin_rule)

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                require(
                    member is not None, f"You does not exists in project - {ticket.project_id}",
                ),
            )

        return any_allowed(*rules)

    async def can_assign_ticket(
            self, subject: Subject, ticket: Ticket, assignee: User,
    ) -> PermissionResult:
        rules = [
            all_allowed(
                *[
                    any_allowed(is_admin_user(user), is_support_user(user))
                    for user in (subject, assignee)
                ]
            )
        ]

        if ticket.project_id:
            assigner_member = await self.member_repo.find(ticket.project_id, subject.id)
            assignee_member = await self.member_repo.find(ticket.project_id, assignee.id)

            project_rule = all_allowed(*[
                all_allowed(
                    require(
                        member is not None,
                        f"You does not exists in project - {ticket.project_id}",
                    ),
                    require(
                        member.has_any_role(MemberRole.staff_roles()),
                        f"Assignee and assigner must be "
                        f"staff of this project - {ticket.project_id}",
                    ),
                )
                for member in (assignee_member, assigner_member)
            ])
            rules.append(project_rule)

        return any_allowed(*rules)

    async def can_archive_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            is_admin_user(subject),
            require(subject.has_role(UserRole.SUPPORT_MANAGER), "Require SUPPORT MANAGER")
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                all_allowed(
                    require(
                        member is not None,
                        f"You does not exists in project - {ticket.project_id}",
                    ),
                    require(
                        member.has_any_role(MemberRole.MANAGER, MemberRole.OWNER),
                        "Project OWNER or MANAGER required",
                    )
                )
            )

        return any_allowed(*rules)

    async def can_edit_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            is_admin_user(subject),
            _is_ticket_reporter(subject, ticket),
            _is_ticket_creator(subject, ticket),
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                all_allowed(
                    require(
                        member is not None,
                        f"You does not exists in project - {ticket.project_id}",
                    ),
                    require(member.has_role(MemberRole.OWNER), "Project OWNER required"),
                )
            )

        return any_allowed(*rules)

    async def can_manage_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            require(subject.has_any_role(*UserRole.support_roles()), "Supports required")
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                all_allowed(
                    require(
                        member is not None,
                        f"You does not exists in project - {ticket.project_id}",
                    ),
                    require(
                        member.has_any_role(*MemberRole.staff_roles()), "Project staff required",
                    ),
                )
            )

        return any_allowed(*rules)

    async def can_close_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            _can_close_ticket_as_customer(subject, ticket),
            _can_close_ticket_as_support(subject, ticket),
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                require(
                    member is not None,
                    f"You does not exists in project - {ticket.project_id}",
                ),
            )

        return any_allowed(*rules)

    async def can_cancel_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [_is_ticket_reporter(subject, ticket), _is_ticket_creator(subject, ticket)]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                require(
                    member is not None,
                    f"You does not exists in project - {ticket.project_id}"
                ),
            )
        else:
            rules.append(
                require(
                    subject.has_any_role(UserRole.SUPPORT_MANAGER, UserRole.ADMIN),
                    "Require SUPPORT_MANAGER or ADMIN",
                )
            )

        return any_allowed(*rules)
