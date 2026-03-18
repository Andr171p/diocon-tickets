from ...core.entities import Attachment
from ..models import AttachmentOrm
from .base import SqlAlchemyRepository


class AttachmentRepository(SqlAlchemyRepository[Attachment, AttachmentOrm]):
    entity = Attachment
    model = AttachmentOrm
