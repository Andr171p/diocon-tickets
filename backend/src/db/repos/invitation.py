from sqlalchemy import select

from ...core.entities import Invitation, UserRole
from ..models import InvitationOrm
from .base import SqlAlchemyRepository


class InvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    entity = Invitation
    model = InvitationOrm

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def find_active_by_email_and_role(self, email: str, role: UserRole) -> Invitation | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email) &
                (self.model.intended_role == role) &
                (not self.model.is_used)
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)
