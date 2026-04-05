from uuid import UUID

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.crm.domain.vo import Inn
from src.iam.domain.entities import Invitation, User
from src.iam.domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from src.iam.domain.vo import UserRole
from src.shared.infra.repos import InMemoryRepository
from src.shared.utils.time import current_datetime


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

    async def get_by_email(self, email: str) -> User | None:
        for user in self.data.values():
            if user.email == email:
                return user
        return None


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
