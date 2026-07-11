import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from uuid import UUID

from src.crm.domain.entities import Counterparty
from src.iam.domain.entities import User
from src.projects.domain.entities import Project


@dataclass(frozen=True, slots=True)
class References:
    """Внешние отношения заявок к другим модулям."""

    users: dict[UUID, User] = field(default_factory=dict)
    counterparties: dict[UUID, Counterparty] = field(default_factory=dict)
    projects: dict[UUID, Project] = field(default_factory=dict)


class ReferenceLoader:
    def __init__(
            self,
            users_loader: Callable[[list[UUID]], Awaitable[list[User]]],
            counterparties_loader: Callable[[list[UUID]], Awaitable[list[Counterparty]]],
            projects_loader: Callable[[list[UUID]], Awaitable[list[Project]]],
    ) -> None:
        self._users_loader = users_loader
        self._counterparties_loader = counterparties_loader
        self._projects_loader = projects_loader

    async def load(
            self,
            *,
            users: Iterable[UUID] = (),
            counterparties: Iterable[UUID] = (),
            projects: Iterable[UUID] = (),
    ) -> References:
        user_ids = list(set(users))
        counterparty_ids = list(set(counterparties))
        project_ids = list(set(projects))

        async with asyncio.TaskGroup() as tg:
            users_task = tg.create_task(
                self._users_loader(user_ids) if user_ids else asyncio.sleep(0, result=[])
            )

            counterparties_task = tg.create_task(
                self._counterparties_loader(counterparty_ids)
                if counterparty_ids
                else asyncio.sleep(0, result=[])
            )

            projects_task = tg.create_task(
                self._projects_loader(project_ids) if project_ids else asyncio.sleep(0, result=[])
            )

        return References(
            users={user.id: user for user in users_task.result()},
            counterparties={
                counterparty.id: counterparty
                for counterparty in counterparties_task.result()
            },
            projects={project.id: project for project in projects_task.result()},
        )


__all__ = ["ReferenceLoader"]
