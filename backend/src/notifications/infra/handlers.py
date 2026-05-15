from typing import Annotated

from faststream import Depends
from faststream.rabbit import RabbitRouter

from ...tickets.domain.events import TicketCreated, TicketReassigned
from ..dependencies import get_notification_service, get_target_resolver
from ..factories import NotificationFactory
from ..resolvers import TargetResolver
from ..services import NotificationService

router = RabbitRouter()


@router.subscriber("tickets.created")
async def on_ticket_created(
        event: TicketCreated,
        target_resolver: Annotated[TargetResolver, Depends(get_target_resolver)],
        service: Annotated[NotificationService, Depends(get_notification_service)],
) -> None:
    targets = await target_resolver.get_targets(event)
    notifications = NotificationFactory.from_ticket_created(event, targets)
    for notification in notifications:
        await service.notify(notification)

@router.subscriber("tickets.reassigned")
async def on_ticket_reassigned(
        event: TicketReassigned,
        target_resolver: Annotated[TargetResolver, Depends(get_target_resolver)],
        service: Annotated[NotificationService, Depends(get_notification_service)],
) -> None:
    
    """
    обрабатываем событие переназначения тикета: находим получателей,
    создаём уведолмение и передаём их в NotificationService
    """

    targets = await target_resolver.get_targets(event)
    notifications = NotificationFactory.from_ticket_reassigned(event, targets)

    for notification in notifications:
        await service.notify(notification)