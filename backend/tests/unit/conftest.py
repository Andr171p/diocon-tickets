from typing import override

from uuid import UUID

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.crm.domain.vo import Inn
from src.iam.domain.entities import Invitation, User
from src.iam.domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from src.iam.domain.vo import UserRole
from src.shared.domain.events import EventPublisher
from src.shared.infra.events import EventBus
from src.shared.infra.repos import InMemoryRepository
from src.shared.schemas import Page, PageParams
from src.shared.utils.time import current_datetime
from src.tickets.domain.entities import Comment, Membership, Project, Ticket
from src.tickets.domain.repos import CommentRepository, ProjectRepository, TicketRepository
from src.tickets.domain.vo import ProjectKey


class InMemoryCounterpartyRepository(InMemoryRepository[Counterparty]):
    async def get_by_email(self, email: str) -> Counterparty | None:
        for entity in self.data.values():
            if entity.email == email:
                return entity
        return None

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        for entity in self.data.values():
            if entity.inn == inn:
                return entity
        return None

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        return [entity for entity in self.data.values() if entity.parent_id == counterparty_id]


class InMemoryUserRepository(InMemoryRepository[User]):

    @override
    async def paginate(
            self, params: PageParams, include_roles: list[UserRole] | None = None
    ) -> Page[User]:
        all_users = list(self.data.values())

        if include_roles is not None:
            allowed_roles = set(include_roles)
            filtered_users = [user for user in all_users if user.role in allowed_roles]
        else:
            filtered_users = all_users

        total_items = len(filtered_users)
        sorted_users = sorted(filtered_users, key=lambda user: user.created_at)
        page_items = sorted_users[params.offset:params.offset + params.size]

        return Page.create(
            items=page_items,
            total_items=total_items,
            page=params.page,
            size=params.size,
        )

    async def get_by_email(self, email: str) -> User | None:
        for user in self.data.values():
            if user.email == email:
                return user
        return None

    async def get_customer_admins(self, counterparty_id: UUID) -> list[User]:
        return [
            user for user in self.data.values()
            if user.counterparty_id == counterparty_id and user.role == UserRole.CUSTOMER_ADMIN
        ]


class InMemoryTokenBlacklist:
    def __init__(self) -> None:
        self.data = {}

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        now = int(current_datetime().timestamp())
        ttl = now - exp
        if ttl <= 0:
            return False

        self.data[jti] = {"revoked_at": current_datetime(), "user_id": user_id, "reason": reason}
        return True

    async def is_revoked(self, jti: UUID) -> bool:
        is_exists = self.data.get(jti)
        return bool(is_exists)


class InMemoryInvitationRepository(InMemoryRepository[Invitation]):
    async def get_by_token(self, token: str) -> Invitation | None:
        for invitation in self.data.values():
            if invitation.token == token:
                return invitation
        return None

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None:
        for invitation in self.data.values():
            if (
                invitation.email == email
                and invitation.assigned_role == user_role
                and not invitation.is_used
            ):
                return invitation
        return None


class InMemoryProjectRepository(InMemoryRepository[Project]):

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        for project in self.data.values():
            if project.key == key:
                return project
        return None

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        existing = set()
        existing_keys = {str(project.key) for project in self.data.values()}
        for key in keys:
            if key in existing_keys:
                existing.add(key)
        return existing

    async def get_membership(self, project_id: UUID, user_id: UUID) -> Membership | None:
        for project in self.data.values():
            if project.id == project_id:
                return next(
                    (
                        membership
                        for membership in project.memberships
                        if membership.user_id == user_id
                    ), None
                )
        return None


class ImMemoryTicketRepository(InMemoryRepository[Ticket]):

    async def get_comments(self, ticket_id: UUID, params: PageParams) -> Page[Comment]: ...

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        counter = 0
        if project_id is not None:
            for ticket in self.data.values():
                if ticket.project_id == project_id:
                    counter += 1

        if counterparty_id is not None:
            for ticket in self.data.values():
                if ticket.counterparty_id == counterparty_id:
                    counter += 1

        return counter


class ImMemoryCommentRepository(InMemoryRepository[Comment]):
    ...


@pytest.fixture
def mock_counterparty_repo() -> CounterpartyRepository:
    return InMemoryCounterpartyRepository()


@pytest.fixture
def mock_user_repo() -> UserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def mock_invitation_repo() -> InvitationRepository:
    return InMemoryInvitationRepository()


@pytest.fixture
def mock_token_blacklist() -> TokenBlacklist:
    return InMemoryTokenBlacklist()


@pytest.fixture
def mock_project_repo() -> ProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture
def mock_ticket_repo() -> TicketRepository:
    return ImMemoryTicketRepository()


@pytest.fixture
def mock_comment_repo() -> CommentRepository:
    return ImMemoryCommentRepository()


@pytest.fixture
def event_publisher() -> EventPublisher:
    return EventBus(max_queue_size=10)
