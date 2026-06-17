from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.events import EventBus
from src.shared.schemas import Pagination
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import CommentType, Priority, Tag, TicketNumber
from src.tickets.infra.repos import (
    SqlCommentRepository,
    SqlReactionRepository,
    SqlTicketRepository,
)
from src.tickets.schemas import CommentCreate, CommentEdit
from src.tickets.services.comment import CommentService


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"comment-manager-{uuid4()}@example.com",
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
def comment_service(session, ticket_repo, comment_repo, reaction_repo):
    return CommentService(
        session=session,
        ticket_repo=ticket_repo,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=EventBus(max_queue_size=10),
    )


def make_ticket(*, reporter_id=None, created_by=None) -> Ticket:
    user_id = created_by or uuid4()

    return Ticket.create(
        ticket_number=TicketNumber(f"COM-26-{uuid4().int % 10**8:08d}"),
        reporter_id=reporter_id or user_id,
        created_by=user_id,
        created_by_role=UserRole.SUPPORT_MANAGER,
        title=f"Comment service ticket {uuid4()}",
        description="Ticket for comment service integration test",
        priority=Priority.HIGH,
        tags=[Tag(name="comments", color="#3498db")],
    )


async def create_saved_ticket(ticket_repo, session, current_user: CurrentUser) -> Ticket:
    ticket = make_ticket(
        reporter_id=current_user.user_id,
        created_by=current_user.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    return ticket


@pytest.mark.asyncio
async def test_reply_to_comment_missing_ticket_returns_404(comment_service, current_support_manager):
    """
    Проверяем reply_to_comment: если тикета нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный ticket_id и случайный parent_comment_id.
    """

    ticket_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
        await comment_service.reply_to_comment(
            ticket_id=ticket_id,
            parent_comment_id=uuid4(),
            data=CommentCreate(
                text="Reply for missing ticket",
                type=CommentType.PUBLIC,
            ),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_reply_to_comment_missing_parent_comment_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем reply_to_comment: если parent-comment не найден,
    сервис должен вернуть NotFoundError.
    Данные: существующий тикет и случайный parent_comment_id.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    parent_comment_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Comment with ID {parent_comment_id} not found"):
        await comment_service.reply_to_comment(
            ticket_id=ticket.id,
            parent_comment_id=parent_comment_id,
            data=CommentCreate(
                text="Reply for missing parent",
                type=CommentType.PUBLIC,
            ),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_reply_to_comment_parent_from_another_ticket_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем reply_to_comment: если parent-comment принадлежит другому тикету,
    сервис должен вернуть NotFoundError.
    Данные: два тикета и комментарий у первого тикета.
    """

    first_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    second_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    parent = await comment_service.add_comment(
        ticket_id=first_ticket.id,
        data=CommentCreate(
            text="Parent comment from another ticket",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    with pytest.raises(NotFoundError, match="Comment does not belong to this ticket"):
        await comment_service.reply_to_comment(
            ticket_id=second_ticket.id,
            parent_comment_id=parent.id,
            data=CommentCreate(
                text="Reply to wrong ticket parent",
                type=CommentType.PUBLIC,
            ),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_edit_comment_missing_comment_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем edit_comment: если комментарий не найден,
    сервис должен вернуть NotFoundError.
    Данные: существующий тикет и случайный comment_id.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    comment_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Comment with ID {comment_id} not found"):
        await comment_service.edit_comment(
            ticket_id=ticket.id,
            comment_id=comment_id,
            data=CommentEdit(text="Updated missing comment"),
            edited_by=current_support_manager.user_id,
        )


@pytest.mark.asyncio
async def test_edit_comment_from_another_ticket_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем edit_comment: если комментарии принадлежит другому тикету,
    сервис должен вернуть NotFoundError.
    Данные: два тикета и комментарий у первого тикета.
    """

    first_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    second_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    comment = await comment_service.add_comment(
        ticket_id=first_ticket.id,
        data=CommentCreate(
            text="Comment from another ticket",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    with pytest.raises(NotFoundError, match="Comment does not belong to this ticket"):
        await comment_service.edit_comment(
            ticket_id=second_ticket.id,
            comment_id=comment.id,
            data=CommentEdit(text="Should not update"),
            edited_by=current_support_manager.user_id,
        )


@pytest.mark.asyncio
async def test_delete_comment_missing_comment_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем delete_comment: если комментарий не найден,
    сервис должен вернуть NotFoundError.
    Данные: существующий тикет и случайный comment_id.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    comment_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Comment with ID {comment_id} not found"):
        await comment_service.delete_comment(
            ticket_id=ticket.id,
            comment_id=comment_id,
            deleted_by=current_support_manager.user_id,
            deleted_by_role=current_support_manager.role,
        )


@pytest.mark.asyncio
async def test_delete_comment_from_another_ticket_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем delete_comment: если комментарий принадлежит другому тикету,
    сервис должен вернуть NotFoundError.
    Данные: два тикета и комментарий у первого тикета.
    """

    first_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)
    second_ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    comment = await comment_service.add_comment(
        ticket_id=first_ticket.id,
        data=CommentCreate(
            text="Comment for amother ticket delete check",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    with pytest.raises(NotFoundError, match="Comment does not belong to this ticket"):
        await comment_service.delete_comment(
            ticket_id=second_ticket.id,
            comment_id=comment.id,
            deleted_by=current_support_manager.user_id,
            deleted_by_role=current_support_manager.role,
        )


@pytest.mark.asyncio
async def test_delete_comment_reply_decrements_parent_reply_count(session, ticket_repo, comment_repo, comment_service, current_support_manager):
    """
    Проверяем delete_comment для reply: при удалении ответа счётчик reply_count
    у родительского комментария должен уменьшиться.
    Данные: тикет, parent-comment и один reply.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    parent = await comment_service.add_comment(
        ticket_id=ticket.id,
        data=CommentCreate(
            text="Parent comment before reply deletion",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    reply = await comment_service.reply_to_comment(
        ticket_id=ticket.id,
        parent_comment_id=parent.id,
        data=CommentCreate(
            text="Reply that will be deleted",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    parent_after_reply = await comment_repo.read(parent.id)
    assert parent_after_reply is not None
    assert parent_after_reply.reply_count == 1

    await comment_service.delete_comment(
        ticket_id=ticket.id,
        comment_id=reply.id,
        deleted_by=current_support_manager.user_id,
        deleted_by_role=current_support_manager.role,
    )

    parent_after_delete = await comment_repo.read(parent.id)
    assert parent_after_delete is not None
    assert parent_after_delete.reply_count == 0


@pytest.mark.asyncio
async def test_get_ticket_comments_missing_ticket_returns_404(comment_service, current_support_manager):
    """
    Проверяем get_comments: если тикета нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный ticket_id.
    """

    ticket_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
        await comment_service.get_comments(
            ticket_id=ticket_id,
            pagination=Pagination(page=1, size=10),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_get_comment_replies_missing_parent_returns_404(comment_service, current_support_manager):
    """
    Проверяем get_comment_replies: если parent-comment не найден,
    сервис должен вернуть NotFoundError.
    Данные: случайный comment_id.
    """

    comment_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Comment with ID {comment_id} not found"):
        await comment_service.get_comment_replies(
            comment_id=comment_id,
            pagination=Pagination(page=1, size=10),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_edit_comment_missing_ticket_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем edit_comment: если тикета нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: существующий комментарий у другого тикета и случайный missing_ticket_id.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    comment = await comment_service.add_comment(
        ticket_id=ticket.id,
        data=CommentCreate(
            text="Comment for missing ticket edit check",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    missing_ticket_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Ticket with ID {missing_ticket_id} not found"):
        await comment_service.edit_comment(
            ticket_id=missing_ticket_id,
            comment_id=comment.id,
            data=CommentEdit(text="Should not uppdate"),
            edited_by=current_support_manager.user_id,
        )

@pytest.mark.asyncio
async def test_delete_comment_missing_ticket_returns_404(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем delete_comment: если тикета нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: существующий комментарий у другого тикета и случайный missing_ticket_id.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    comment = await comment_service.add_comment(
        ticket_id=ticket.id,
        data=CommentCreate(
            text="Comment for missing ticket delete check",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    missing_ticket_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Ticket with ID {missing_ticket_id} not found"):
        await comment_service.delete_comment(
            ticket_id=missing_ticket_id,
            comment_id=comment.id,
            deleted_by=current_support_manager.user_id,
            deleted_by_role=current_support_manager.role,
        )


@pytest.mark.asycnio
async def test_get_comments_denies_customer_without_access(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем get_commnets: customer без доступа к тикету
    не должен видеть комментарии.
    Данные: тикет support-пользователя и другой customer.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    customer = CurrentUser(
        user_id=uuid4(),
        email=f"comment-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    with pytest.raises(PermissionDeniedError):
        await comment_service.get_comments(
            ticket_id=ticket.id,
            pagination=Pagination(page=1, size=10),
            current_user=customer,
        )


@pytest.mark.asyncio
async def test_get_comment_replies_denies_customer_without_access(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем get_comments_replies: customer без доступа к тикету
    не должен видеть ответы на комментарий.
    Данные: тикет support-пользоваетля, parent-comment и другой customer.
    """

    ticket = await create_saved_ticket(ticket_repo, session, current_support_manager)

    parent = await comment_service.add_comment(
        ticket_id=ticket.id,
        data=CommentCreate(
            text="Parent comment for denied replies access",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    customer = CurrentUser(
        user_id=uuid4(),
        email=f"reply-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    with pytest.raises(PermissionDeniedError):
        await comment_service.get_comment_replies(
            comment_id=parent.id,
            pagination=Pagination(page=1, size=10),
            current_user=customer,
        )


@pytest.mark.asyncio
async def test_get_replies_include_internal_denies_customer(session, ticket_repo, comment_service, current_support_manager):
    """
    Проверяем get_comment_replies: customer с доступном к тикету
    не должен видеть internal replies через include_internal=True.
    Данные: тикет, где customer является reporter, и parent-comment от support.
    """

    customer_id = uuid4()
    counterparty_id = uuid4()

    customer = CurrentUser(
        user_id=customer_id,
        email=f"internal-replies-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=counterparty_id,
    )

    ticket = Ticket.create(
        ticket_number=TicketNumber(f"COM-26-{uuid4().int % 10**8:08d}"),
        reporter_id=customer.user_id,
        created_by=current_support_manager.user_id,
        created_by_role=current_support_manager.role,
        title=f"Ticket for internal replies check {uuid4()}",
        description="Ticket for comment service integration test",
        priority=Priority.HIGH,
        counterparty_id=customer.counterparty_id,
        tags=[Tag(name="comments", color="#3498db")],
    )

    await ticket_repo.create(ticket)
    await session.commit()

    parent = await comment_service.add_comment(
        ticket_id=ticket.id,
        data=CommentCreate(
            text="Parent comment for internal replies check",
            type=CommentType.PUBLIC,
        ),
        current_user=current_support_manager,
    )

    with pytest.raises(PermissionDeniedError, match="Only support team can view internal comments"):
        await comment_service.get_comment_replies(
            comment_id=parent.id,
            pagination=Pagination(page=1, size=10),
            current_user=customer,
            include_internal=True,
        )