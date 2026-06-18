from uuid import uuid4

import pytest

import src.projects.infra.models
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.events import EventBus
from src.tickets.domain.entities import Comment, Ticket
from src.tickets.domain.vo import CommentType, Priority, ReactionType, Tag, TicketNumber
from src.tickets.infra.repos import (
    SqlCommentRepository,
    SqlReactionRepository,
    SqlTicketRepository,
)
from src.tickets.services.reaction import ReactionService


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"reaction-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def comment_repo(session):
    return SqlCommentRepository(session)


@pytest.fixture
def reaction_repo(session):
    return SqlReactionRepository(session)


@pytest.fixture
def reaction_service(session, comment_repo, reaction_repo):
    return ReactionService(
        session=session,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=EventBus(max_queue_size=10),
    )


def make_ticket(current_user: CurrentUser) -> Ticket:
    return Ticket.create(
        ticket_number=TicketNumber(f"RCT-26-{uuid4().int % 10**8:08d}"),
        reporter_id=current_user.user_id,
        created_by=current_user.user_id,
        created_by_role=current_user.role,
        title=f"Reaction service ticket {uuid4()}",
        description="Ticket for reaction service integration test",
        priority=Priority.HIGH,
        tags=[Tag(name="reactions", color="#3498db")],
    )


async def create_saved_comment(
    session,
    ticket_repo,
    comment_repo,
    current_user: CurrentUser,
    *,
    deleted: bool = False,
) -> Comment:
    ticket = make_ticket(current_user)

    await ticket_repo.create(ticket)
    await session.commit()

    comment = Comment.create(
        ticket_id=ticket.id,
        author_id=current_user.user_id,
        author_role=current_user.role,
        text=f"Comment for reaction service {uuid4()}",
        comment_type=CommentType.PUBLIC,
    )

    if deleted:
        comment.delete(
            deleted_by=current_user.user_id,
            deleted_by_role=current_user.role,
        )

    await comment_repo.create(comment)
    await session.commit()

    return comment


@pytest.mark.asyncio
async def test_toggle_missing_comment_returns_404(reaction_service, current_support_manager):
    """
    Проверяем toggle: если комментария нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный comment_id.
    """

    comment_id = uuid4()

    with pytest.raises(
        NotFoundError,
        match=f"Comment with ID {comment_id} not found",
    ):
        await reaction_service.toggle(
            comment_id=comment_id,
            current_user=current_support_manager,
            reaction_type=ReactionType.LIKE,
        )


@pytest.mark.asyncio
async def test_toggle_deleted_comment_returns_404(session, ticket_repo, comment_repo, reaction_service, current_support_manager):
    """
    Проверяем toggle: удалённый комментарий не принимает реакции,
    поэтому сервис должен вернуть NotFoundError.
    Данные: сохранённый и затем удалённый комментарий.
    """
        
    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager, deleted=True)

    with pytest.raises(
        NotFoundError,
        match=f"Comment with ID {comment.id} not found",
    ):
        await reaction_service.toggle(
            comment_id=comment.id,
            current_user=current_support_manager,
            reaction_type=ReactionType.LIKE,
        )


@pytest.mark.asyncio
async def test_toggle_creates_reaction(session, ticket_repo, comment_repo, reaction_repo, reaction_service, current_support_manager):
    """
    Проверяем toggle: если реакции ещё нет,
    сервис должен создать и сохранить её в БД.
    Данные: существующий комментарий и реакции LIKE.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager)

    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.LIKE,
    )

    reaction = await reaction_repo.find(
        comment_id=comment.id,
        author_id=current_support_manager.user_id,
        reaction_type=ReactionType.LIKE,
    )

    assert reaction is not None
    assert reaction.comment_id == comment.id
    assert reaction.author_id == current_support_manager.user_id
    assert reaction.reaction_type == ReactionType.LIKE


@pytest.mark.asyncio
async def test_toggle_same_reaction_deletes_reaction(session, ticket_repo, comment_repo, reaction_repo, reaction_service, current_support_manager):
    """
    Проверяем toggle: повторная установка той же реакции
    должна удалить ранее сохранённую реакцию.
    Данные: существующий комментарий и два последовательных LIKE.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager)

    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.LIKE,
    )
    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.LIKE,
    )

    reaction = await reaction_repo.find(
        comment_id=comment.id,
        author_id=current_support_manager.user_id,
        reaction_type=ReactionType.LIKE,
    )

    assert reaction is None


@pytest.mark.asyncio
async def test_toggle_allows_multiple_reaction_types_from_same_user(session, ticket_repo, comment_repo, reaction_repo, reaction_service, current_support_manager):
    """
    Проверяем toggle: один пользователь может установить несколько
    разных реакций на один комментарий.
    Данные: существующий комментарий, реакции LIKE и THANKS.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager)

    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.LIKE,
    )
    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.THANKS,
    )

    like = await reaction_repo.find(
        comment_id=comment.id,
        author_id=current_support_manager.user_id,
        reaction_type=ReactionType.LIKE,
    )
    thanks = await reaction_repo.find(
        comment_id=comment.id,
        author_id=current_support_manager.user_id,
        reaction_type=ReactionType.THANKS,
    )

    assert like is not None
    assert thanks is not None
    assert like.id != thanks.id


@pytest.mark.asyncio
async def test_get_reactions_returns_counts_and_current_user_reactions(session, ticket_repo, comment_repo, reaction_service, current_support_manager):
    """
    Проверяем get_reactions_for_comment: сервис должен вернуть общие
    счётчики и реакции, установленные текущим пользователем.
    Данные: два пользователя и несколько реакций разных типов.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager)

    other_user = CurrentUser(
        user_id=uuid4(),
        email=f"reaction-agent-{uuid4()}@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.LIKE,
    )
    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=current_support_manager,
        reaction_type=ReactionType.THANKS,
    )
    await reaction_service.toggle(
        comment_id=comment.id,
        current_user=other_user,
        reaction_type=ReactionType.LIKE,
    )

    response = await reaction_service.get_reactions_for_comment(
        comment_id=comment.id,
        current_user=current_support_manager,
    )

    assert response.reaction_counts[ReactionType.LIKE] == 2
    assert response.reaction_counts[ReactionType.THANKS] == 1
    assert set(response.user_reactions) == {
        ReactionType.LIKE,
        ReactionType.THANKS,
    }


@pytest.mark.asyncio
async def test_get_reactions_missing_comment_returns_404(reaction_service, current_support_manager):
    """
    Проверяем get_reactions_for_comment: если комментария нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный comment_id.
    """

    comment_id = uuid4()

    with pytest.raises(
        NotFoundError,
        match=f"Comment with ID {comment_id} not found",
    ):
        await reaction_service.get_reactions_for_comment(
            comment_id=comment_id,
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_get_reactions_deleted_comment_returns_404(session, ticket_repo, comment_repo, reaction_service, current_support_manager):
    """
    Проверяем get_reactions_for_comment: для удалённого комментария
    сервис должен вернуть NotFoundError.
    Данные: сохранённый и затём удалённый комментарий.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager, deleted=True)

    with pytest.raises(
        NotFoundError,
        match=f"Comment with ID {comment.id} not found",
    ):
        await reaction_service.get_reactions_for_comment(
            comment_id=comment.id,
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_toggle_customer_in_progress_reaction_denied(session, ticket_repo, comment_repo, reaction_repo, reaction_service, current_support_manager):
    """
    Проверяем toggle: customer не может установить реакцию IN_PROGRESS.
    Сервис должен вернуть PermissionDeniedError и не сохранить реакцию.
    Данные: существующий комментарий и пользователь с ролью CUSTOMER.
    """

    comment = await create_saved_comment(session, ticket_repo, comment_repo, current_support_manager)

    customer = CurrentUser(
        user_id=uuid4(),
        email=f"reaction-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    with pytest.raises(
        PermissionDeniedError,
        match="Customers cannot set 'In Progress' reaction",
    ):
        await reaction_service.toggle(
            comment_id=comment.id,
            current_user=customer,
            reaction_type=ReactionType.IN_PROGRESS,
        )

    reaction = await reaction_repo.find(
        comment_id=comment.id,
        author_id=customer.user_id,
        reaction_type=ReactionType.IN_PROGRESS,
    )

    assert reaction is None