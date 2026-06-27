from __future__ import annotations

from typing import Self

from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from .entities import Task
from .exceptions import NotAllowedStatusTransitionError
from .vo import TaskStatus

TransitionAction = Callable[[Task, UUID], None] | Callable[[Task], None]


@dataclass(frozen=True)
class StatusTransition:
    """
    Переход из одного статуса задачи в другой.
    """

    from_status: TaskStatus
    to_status: TaskStatus
    actions: tuple[TransitionAction, ...]


@dataclass
class TaskWorkflow:
    """
    Управляет состоянием и переходами между статусами задачи.
    """

    transitions: dict[
        tuple[TaskStatus, TaskStatus], tuple[TransitionAction, ...]
    ] = field(default_factory=dict)

    def allow(
            self,
            from_status: TaskStatus,
            to_status: TaskStatus,
            *actions: TransitionAction
    ) -> Self:
        transition = (from_status, to_status)
        if transition not in self.transitions:
            self.transitions[transition] = actions

        return self

    def resolve(self, old_status: TaskStatus, new_status: TaskStatus) -> StatusTransition:
        transition = (old_status, new_status)
        if transition not in self.transitions:
            raise NotAllowedStatusTransitionError(
                f"Not allowed status transition from {old_status} to {new_status}."
            )

        actions = self.transitions[transition]
        return StatusTransition(from_status=old_status, to_status=new_status, actions=actions)


task_workflow = (
    TaskWorkflow()
    # =============
    # From backlog
    # =============
    .allow(
        TaskStatus.BACKLOG, TaskStatus.TODO,
        Task.start_work
    )
    .allow(
        TaskStatus.BACKLOG, TaskStatus.CANCELLED,
        Task.unassign, Task.reset_reviewer,
    )
    # ============
    # From todo
    # ============
    .allow(
        TaskStatus.TODO, TaskStatus.BACKLOG,
        Task.unassign, Task.reset_reviewer,
    )
    .allow(
        TaskStatus.TODO, TaskStatus.IN_PROGRESS,
        Task.start_work,
    )
    .allow(
        TaskStatus.TODO, TaskStatus.PAUSED,
        Task.finish_work,
    )
    .allow(
        TaskStatus.TODO, TaskStatus.CANCELLED,
        Task.unassign, Task.reset_reviewer,
    )
)
