from src.media.infra.repo import AttachmentMapper
from src.shared.domain.vo import Tag
from src.shared.infra.repos import ModelMapper

from ..domain.entities import Ticket
from ..domain.vo import TicketNumber
from .models import TicketOrm


class TicketMapper(ModelMapper[Ticket, TicketOrm]):
    @staticmethod
    def to_entity(model: TicketOrm) -> Ticket:
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            product_id=model.product_id,
            created_by=model.created_by,
            approved_by=model.approved_by,
            resolved_by=model.resolved_by,
            closed_by=model.closed_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            type=model.ticket_type,
            status=model.status,
            priority=model.priority,
            assignee_id=model.assignee_id,
            approved_at=model.approved_at,
            resolved_at=model.resolved_at,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            attachments=[
                AttachmentMapper.to_entity(attachment) for attachment in model.attachments
            ],
        )

    @staticmethod
    def to_light(model: TicketOrm) -> Ticket:
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            product_id=model.product_id,
            created_by=model.created_by,
            approved_by=model.approved_by,
            resolved_by=model.resolved_by,
            closed_by=model.closed_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            type=model.ticket_type,
            status=model.status,
            priority=model.priority,
            assignee_id=model.assignee_id,
            approved_at=model.approved_at,
            resolved_at=model.resolved_at,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            attachments=[],
        )

    @staticmethod
    def from_entity(entity: Ticket) -> TicketOrm:
        return TicketOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            project_id=entity.project_id,
            counterparty_id=entity.counterparty_id,
            product_id=entity.product_id,
            created_by=entity.created_by,
            approved_by=entity.approved_by,
            resolved_by=entity.resolved_by,
            closed_by=entity.closed_by,
            reporter_id=entity.reporter_id,
            number=entity.number.value,
            title=entity.title,
            description=entity.description,
            ticket_type=entity.type,
            status=entity.status,
            priority=entity.priority,
            assignee_id=entity.assignee_id,
            approved_at=entity.approved_at,
            resolved_at=entity.resolved_at,
            closed_at=entity.closed_at,
            tags=[{"name": tag.name, "color": tag.color} for tag in entity.tags],
            attachments=[
                AttachmentMapper.from_entity(attachment) for attachment in entity.attachments
            ],
        )
