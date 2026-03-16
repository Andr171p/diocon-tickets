from uuid import UUID

from sqlalchemy import select, update

from ...core.entities import RefreshToken
from ...utils.commons import current_datetime
from ..models import RefreshTokenOrm
from .base import SqlAlchemyRepository


class RefreshTokenRepository(SqlAlchemyRepository[RefreshToken, RefreshTokenOrm]):
    entity = RefreshToken
    model = RefreshTokenOrm

    async def get_by_token(self, token: str) -> RefreshToken | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def revoke(self, token_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == token_id)
            .values(revoked=True, revoked_at=current_datetime())
        )
        await self.session.execute(stmt)
