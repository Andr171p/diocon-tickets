from typing import override

from sqlalchemy import Select, cast, select
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR

from src.shared.infra.repos import ModelMapper, SqlAlchemyRepository
from src.shared.schemas import Page, Pagination

from ..domain.entities import Invitation, User
from ..domain.repos import UserFilters
from ..domain.vo import Email, FullName, PasswordHash, Username, UserRole
from .models import InvitationOrm, UserOrm


class UserMapper(ModelMapper[User, UserOrm]):
    @staticmethod
    def to_entity(model: UserOrm) -> User:
        return User(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=Email(model.email),
            username=None if model.username is None else Username(model.username),
            full_name=None if model.full_name is None else FullName(model.full_name),
            avatar_url=model.avatar_url,
            counterparty_id=model.counterparty_id,
            roles=set(model.roles),
            password_hash=PasswordHash(model.password_hash),
            is_active=model.is_active,
        )

    @staticmethod
    def from_entity(entity: User) -> UserOrm:
        return UserOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            email=entity.email.value,
            username=None if entity.username is None else entity.username.value,
            full_name=None if entity.full_name is None else entity.full_name.value,
            avatar_url=entity.avatar_url,
            counterparty_id=entity.counterparty_id,
            roles=list(entity.roles),
            password_hash=entity.password_hash.get_hashed_value(),
            is_active=entity.is_active,
        )


class SqlUserRepository(SqlAlchemyRepository[User, UserOrm]):
    model = UserOrm
    model_mapper = UserMapper

    def _apply_user_filters(
            self, stmt: Select[tuple[UserOrm]], filters: UserFilters
    ) -> Select[tuple[UserOrm]]:
        if filters.roles is not None and filters.roles:
            roles_as_strings: list[str] = [role.value for role in filters.roles]
            stmt = stmt.where(cast(self.model.roles, ARRAY(VARCHAR)).has_any(roles_as_strings))

        if filters.counterparty_id is not None:
            stmt = stmt.where(self.model.counterparty_id == filters.counterparty_id)

        return stmt

    @override
    async def paginate(
            self, pagination: Pagination, filters: UserFilters | None = None
    ) -> Page[User]:
        stmt = select(self.model)

        if filters:
            stmt = self._apply_user_filters(stmt, filters)

        return await self._paginate(stmt, pagination)

    async def get_by_email(self, email: Email) -> User:
        stmt = select(self.model).where(self.model.email == email.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)


class InvitationMapper(ModelMapper[Invitation, InvitationOrm]):
    @staticmethod
    def to_entity(model: InvitationOrm) -> Invitation:
        return Invitation(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=Email(model.email),
            token=model.token,
            invited_by=model.invited_by,
            granted_roles=set(model.granted_roles),
            counterparty_id=model.counterparty_id,
            expires_at=model.expires_at,
            used_at=model.used_at,
            is_used=model.is_used,
        )

    @staticmethod
    def from_entity(entity: Invitation) -> InvitationOrm:
        return InvitationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            email=entity.email.value,
            token=entity.token,
            invited_by=entity.invited_by,
            granted_roles=list(entity.granted_roles),
            counterparty_id=entity.counterparty_id,
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            is_used=entity.is_used,
        )


class SqlInvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    model = InvitationOrm
    model_mapper = InvitationMapper

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_active(self, email: Email, roles: set[UserRole]) -> Invitation | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email.value) &
                (self.model.granted_roles.contains(list(roles))) &
                (self.model.is_used.is_(False))
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
