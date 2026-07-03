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

    def can_create_feedback(
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
    
    @staticmethod
    def can_view_feedback(
        subject: Subject,
        feedback: Feedback | None = None,
    ) -> PermissionResult:
        """
        Проверяет, может ли субъект посмотреть отзыв или список отзывов.
        """

        if feedback is None:
            return IsSupportRule(subject).check()

        policy = AnyOf(
            IsFeedbackAuthorRule(subject, feedback),
            IsSupportRule(subject),
        )

        return policy.check()
    
    @staticmethod
    def can_update_feedback(
        subject: Subject, 
        feedback: Feedback,
    ) -> PermissionResult:
        """
        Проверяет, может ли субъект редактировать отзыв.
        """

        policy = AnyOf(
            IsFeedbackAuthorRule(subject, feedback),
            IsSupportRule(subject),
        )

        return policy.check()

    @staticmethod
    def can_archive_feedback(
        subject: Subject,
        feedback: Feedback,
    ) -> PermissionResult:
        """
        Проверяет может ли субъект архивировать отзыв.
        """

        policy = AnyOf(
            IsFeedbackAuthorRule(subject, feedback),
            IsSupportRule(subject),
        )

        return policy.check()

