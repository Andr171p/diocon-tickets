from src.iam.domain.authz import AllOf, AnyOf, PermissionResult, Subject
from src.tickets.domain.entities import Ticket

from .entities import Feedback
from .rules import (
    IsCustomerRule,
    IsFeedbackAuthorRule,
    IsSupportRule,
    IsTicketClosedRule,
    IsTicketReporterRule,
)

class FeedbackAuthZService:
    """
    Доменный сервис авторизации для отзывов.
    Собирает атомарные правила в политики доступа для конкретных действий.
    """

    async def can_create_feedback(
            self,
            subject: Subject,
            ticket: Ticket,
    ) -> PermissionResult:
        """
        Проверяет, может ли субъект оставить отзыв по тикету.
        """

        policy = AllOf(
            IsCustomerRule(subject),
            IsTicketReporterRule(subject, ticket),
            IsTicketClosedRule(ticket),
        )
        return policy.check()