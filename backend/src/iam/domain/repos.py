from typing import Protocol, override

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from ..domain.vo import UserRole
from .entities import Invitation, User
from .vo import Email


@dataclass(frozen=True)
class UserFilters:
    roles: set[UserRole] | None = None
    counterparty_id: UUID | None = None


class UserRepository(Repository[User]):

    @override
    async def paginate(
            self, pagination: Pagination, filters: UserFilters | None = None
    ) -> Page[User]: ...

    async def get_by_email(self, email: Email) -> User | None: ...


class TokenStore(Protocol):

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool: ...

    async def is_revoked(self, jti: UUID) -> bool: ...


class InvitationRepository(Repository[Invitation]):

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active(self, email: Email, roles: set[UserRole]) -> Invitation | None: ...
