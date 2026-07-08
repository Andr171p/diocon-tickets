from uuid import UUID

from src.iam.domain.authz import AllOf, AnyOf, PermissionResult, Subject
from src.iam.domain.entities import User
from src.iam.domain.rules import HasAnyUserRoleRule, IsAdminRule, IsStaffRule, IsSupportRule
from src.iam.domain.vo import UserRole
from src.projects.domain.repos import ProjectMemberRepository
from src.projects.domain.rules import (
    HasAnyMemberRoleRule,
    IsMemberExistsRule,
    IsProjectOwnerOrManagerRule,
    IsProjectStaffRule,
)
from src.projects.domain.vo import MemberRole

from .entities import Ticket
from .rules import (
    IsTicketAssigneeRule,
    IsTicketCreatorRule,
    IsTicketReporterRule,
    SameCounterpartyRule,
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
        rules = [IsAdminRule(subject), SameCounterpartyRule(subject, counterparty_id)]

        if project_id:
            member = await self.member_repo.find(project_id, subject.id)
            rules.append(IsMemberExistsRule(member))

        return AnyOf(*rules).check()

    async def can_access_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            IsStaffRule(subject),
            IsTicketReporterRule(subject, ticket),
            IsTicketCreatorRule(subject, ticket),
        ]
        customer_admin_rule = AllOf(
            HasAnyUserRoleRule(subject, required_roles=[UserRole.CUSTOMER_ADMIN]),
            SameCounterpartyRule(subject, ticket.counterparty_id)
        )
        rules.append(customer_admin_rule)

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(IsMemberExistsRule(member))

        return AnyOf(*rules).check()

    async def can_assign_ticket(
            self, subject: Subject, ticket: Ticket, assignee: User,
    ) -> PermissionResult:
        users_rule = AllOf(
            *[AnyOf(IsAdminRule(user), IsSupportRule(user)) for user in (subject, assignee)]
        )
        rules = [users_rule]

        if ticket.project_id:
            assigner_member = await self.member_repo.find(ticket.project_id, subject.id)
            assignee_member = await self.member_repo.find(ticket.project_id, assignee.id)

            members_rule = AllOf(
                *[
                    AllOf(IsMemberExistsRule(member), IsProjectStaffRule(member))
                    for member in (assigner_member, assignee_member)
                  ]
            )
            rules.append(members_rule)

        return AnyOf(*rules).check()

    async def can_archive_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            IsAdminRule(subject),
            HasAnyUserRoleRule(subject, required_roles=[UserRole.SUPPORT_MANAGER])
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                AllOf(IsMemberExistsRule(member), IsProjectOwnerOrManagerRule(member))
            )

        return AnyOf(*rules).check()

    @staticmethod
    def can_edit_ticket(subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [
            IsAdminRule(subject),
            IsTicketReporterRule(subject, ticket),
            IsTicketCreatorRule(subject, ticket),
        ]
        return AnyOf(*rules).check()

    async def can_track_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        """
        Может использоваться для авторизации действий:
         - start_progress
         - resolve
         - pause
        """

        rules = [
            IsAdminRule(subject),
            IsTicketAssigneeRule(subject, ticket),
        ]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                HasAnyMemberRoleRule(
                    member, required_roles=[MemberRole.OWNER, MemberRole.MANAGER]
                )
            )
        else:
            rules.append(HasAnyUserRoleRule(subject, required_roles=[UserRole.SUPPORT_MANAGER]))

        return AnyOf(*rules).check()

    async def can_close_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)

            project_rules = [
                AllOf(
                    HasAnyMemberRoleRule(member, required_roles=[MemberRole.CUSTOMER]),
                    IsTicketReporterRule(subject, ticket),
                ),
                AllOf(
                    HasAnyMemberRoleRule(member, required_roles=[MemberRole.CUSTOMER_MANAGER]),
                    SameCounterpartyRule(subject, ticket.counterparty_id)
                ),
                IsProjectStaffRule(member),
            ]

            return AnyOf(*project_rules).check()

        rules = [
            AllOf(
                HasAnyUserRoleRule(subject, required_roles=[UserRole.CUSTOMER]),
                IsTicketReporterRule(subject, ticket),
            ),
            AllOf(
                HasAnyUserRoleRule(subject, required_roles=[UserRole.CUSTOMER_ADMIN]),
                SameCounterpartyRule(subject, ticket.counterparty_id),
            ),
            AllOf(
                HasAnyUserRoleRule(subject, required_roles=[UserRole.SUPPORT_AGENT]),
                IsTicketAssigneeRule(subject, ticket),
            ),
            HasAnyUserRoleRule(subject, required_roles=[UserRole.SUPPORT_MANAGER, UserRole.ADMIN]),
        ]

        return AnyOf(*rules).check()

    async def can_cancel_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [IsTicketCreatorRule(subject, ticket), IsTicketReporterRule(subject, ticket)]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(IsProjectOwnerOrManagerRule(member))
        else:
            rules.append(
                HasAnyUserRoleRule(
                    subject, required_roles=[UserRole.SUPPORT_MANAGER, UserRole.ADMIN]
                )
            )

        return AnyOf(*rules).check()

    async def can_resolve_ticket(self, subject: Subject, ticket: Ticket) -> PermissionResult:
        rules = [IsTicketAssigneeRule(subject, ticket)]

        if ticket.project_id:
            member = await self.member_repo.find(ticket.project_id, subject.id)
            rules.append(
                HasAnyMemberRoleRule(member, required_roles=[MemberRole.OWNER, MemberRole.MANAGER])
            )
        else:
            rules.append(HasAnyUserRoleRule(subject, required_roles=[UserRole.SUPPORT_MANAGER]))

        return AnyOf(*rules).check()
