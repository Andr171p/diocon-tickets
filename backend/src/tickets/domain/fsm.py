from typing import Concatenate, ParamSpec, TypeVar

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps

from src.shared.domain.exceptions import InvalidStateError

from .entities import Ticket
from .vo import TicketStatus

P = ParamSpec("P")
T = TypeVar("T", bound=Ticket)


@dataclass(frozen=True, slots=True)
class Transition:
    from_: set[TicketStatus]
    to: TicketStatus | None = None

    @property
    def changes_status(self) -> bool:
        return self.to is not None


def transition(*from_: TicketStatus, to: TicketStatus | None = None):
    transition_ = Transition(from_=set(from_), to=to)

    def decorator(func: Callable[Concatenate[T, P], None]) -> Callable[Concatenate[T, P], None]:
        sig = inspect.signature(func)

        @wraps(func)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> None:

            if self.status not in transition_.from_:
                raise InvalidStateError(f"Invalid ticket transition from {self.status} to {to}.")

            bound = sig.bind_partial(self, *args, **kwargs)

            if "actor_id" not in bound.arguments:
                raise RuntimeError(f"{func.__qualname__} must define actor_id")

            actor_id = bound.arguments["actor_id"]

            func(self, *args, **kwargs)

            if transition_.to:
                self.change_status(transition_.to, actor_id)

        wrapper.__transition__ = transition_  # type: ignore[attr-defined]

        return wrapper

    return decorator
