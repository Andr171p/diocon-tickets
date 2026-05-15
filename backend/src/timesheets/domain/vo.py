from enum import StrEnum


class WorklogStatus(StrEnum):
    """Статус записи о потраченном времени"""

    DRAFT = "draft"  # черновик
    SUBMITTED = "submitted"  # на согласовании
    APPROVED = "approved"  # согласовано
    REJECTED = "rejected"  # отклонено

    def is_editable(self) -> bool:
        """Можно ли редактировать запись"""

        return self == self.DRAFT

    def is_final(self) -> bool:
        """"""

        return self in {self.APPROVED, self.REJECTED}
