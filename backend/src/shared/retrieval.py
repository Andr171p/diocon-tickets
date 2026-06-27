from collections.abc import Awaitable, Callable
from uuid import UUID

from .domain.entities import Entity
from .domain.exceptions import NotFoundError


async def get_or_raise_404[EntityT: Entity](
        loader: Callable[[UUID, ...], Awaitable[EntityT | None]],
        uid: UUID,
        aggregate_type: type[EntityT],
) -> EntityT:
    obj = await loader(uid)
    if obj is None:
        raise NotFoundError(f"{aggregate_type.__class__.__name__} with ID {uid} not found")

    return obj
