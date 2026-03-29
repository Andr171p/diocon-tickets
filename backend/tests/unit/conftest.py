from datetime import datetime
from uuid import UUID

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.crm.domain.vo import Inn
from src.iam.domain.entities import Invitation, User
from src.iam.domain.repos import InvitationRepository, UserRepository
from src.iam.domain.vo import UserRole
from src.iam.schemas import TokenData
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
    def __init__(self):
        super().__init__()
        self.tokens: dict[str, TokenData] = {}

    async def get_by_email(self, email: str) -> User | None:
        for user in self.data.values():
            if user.email == email:
                return user
        return None

    async def store_token(self, user_id: UUID, token: str, expires_at: datetime) -> None:
        self.tokens[token] = TokenData(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            revoked=False,
            revoked_at=None,
        )

    async def get_token_data(self, token: str) -> TokenData | None:
        return self.tokens.get(token)

    async def revoke_token(self, token: str) -> None:
        if token in self.tokens:
            token_data = self.tokens[token]
            token_data.revoked = True
            token_data.revoked_at = current_datetime()
            self.tokens[token] = token_data


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
