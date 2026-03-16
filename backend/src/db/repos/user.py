from sqlalchemy import select

from ...core.entities import User
from ..models import UserOrm
from .base import SqlAlchemyRepository


class UserRepository(SqlAlchemyRepository[User, UserOrm]):
    entity = User
    model = UserOrm

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)
