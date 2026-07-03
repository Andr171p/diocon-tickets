from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query

from src.shared.dependencies import EventPublisherDep, SessionDep
from src.tickets.dependencies import TicketRepoDep

from .domain.authz import FeedbackAuthZService
from .domain.repos import FeedbackFilters, FeedbackRepository
from .infra.repos import SqlFeedbackRepository
from .services.feedback import FeedbackService


def get_feedback_repo(session: SessionDep) -> SqlFeedbackRepository:
    """
    Создать SQLAlchemy-репозиторий отзывов.
    """

    return SqlFeedbackRepository(session)


FeedbackRepoDep = Annotated[FeedbackRepository, Depends(get_feedback_repo)]


def get_feedback_authz_service() -> FeedbackAuthZService:
    """
    Создать доменный сервис авторизации отзывов.
    """

    return FeedbackAuthZService()


FeedbackAuthZServiceDep = Annotated[
    FeedbackAuthZService,
    Depends(get_feedback_authz_service),
]


def get_feedback_service(
        session: SessionDep,
        feedback_repo: FeedbackRepoDep,
        ticket_repo: TicketRepoDep,
        authz_service: FeedbackAuthZServiceDep,
        event_publisher: EventPublisherDep,
) -> FeedbackService:
    """
    Создать application service для работы с отзывами.
    """

    return FeedbackService(
        uow=session,
        feedback_repo=feedback_repo,
        ticket_repo=ticket_repo,
        authz_service=authz_service,
        event_publisher=event_publisher,
    )


FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]


def get_feedback_filters(
        rating: Annotated[
            int | None,
            Query(ge=1, le=5, description="Фильтр по оценке от 1 до 5"),
        ] = None,
        ticket_id: Annotated[
            UUID | None,
            Query(alias="ticketId", description="Фильтр по ID тикета"),
        ] = None,
        author_id: Annotated[
            UUID | None,
            Query(description="Фильтр по ID автора отзыва")
        ] = None,
) -> FeedbackFilters:
    """
    Собрать фильтры списка отзывов из query-параметров.
    """

    return FeedbackFilters(
        rating=rating,
        ticket_id=ticket_id,
        author_id=author_id,
    )


FeedbackFiltersDep = Annotated[FeedbackFilters, Depends(get_feedback_filters)]