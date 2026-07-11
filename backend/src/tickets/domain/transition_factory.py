from collections.abc import Callable
from dataclasses import dataclass

from .vo import TicketAction, TicketStatus

TransitionHandler = Callable[..., None]


@dataclass(frozen=True, slots=True)
class Transition:
    to: TicketStatus | None = None
    handler: TransitionHandler | None = None

    @property
    def changes_status(self) -> bool:
        return self.to is not None


_transition_registry: dict[tuple[TicketStatus, TicketAction], Transition] = {}


def register_transition(
        *from_: TicketStatus, action: TicketAction, to: TicketStatus | None = None,
) -> None:
    """Регистрация перехода без дополнительной логики."""

    for state in from_:
        key = (state, action)
        if key in _transition_registry:
            raise RuntimeError(f"Transition already registered: {state.value}/{action.value}")

        _transition_registry[key] = Transition(to=to)


def transition(*from_: TicketStatus, action: TicketAction, to: TicketStatus | None = None):

    def wrapper(func: TransitionHandler) -> TransitionHandler:
        for state in from_:
            key = (state, action)

            if key in _transition_registry:
                raise RuntimeError(f"Transition already registered: {state.value}/{action.value}")

            _transition_registry[key] = Transition(to=to, handler=func)

        return func

    return wrapper


def get_transition(from_: TicketStatus, action: TicketAction) -> Transition | None:
    return _transition_registry.get((from_, action))
