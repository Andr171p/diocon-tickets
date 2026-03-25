from datetime import datetime
from uuid import UUID

from ...shared.domain.repo import Repository
from ..domain.vo import UserRole
from ..schemas import TokenData
from .entities import Invitation, User


class UserRepository(Repository[User]):

    async def get_by_email(self, email: str) -> User | None: ...

    async def store_token(self, user_id: UUID, token: str, expires_at: datetime) -> None: ...

    async def get_token_data(self, token: str) -> TokenData | None: ...

    async def revoke_token(self, token: str) -> None: ...


class InvitationRepository(Repository[Invitation]):

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None: ...
