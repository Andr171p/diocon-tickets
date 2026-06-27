from fastapi import status

from src.shared.domain.exceptions import AppError


class NotAllowedStatusTransitionError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "NOT_ALLOWED_STATUS_TRANSITION"
    public_message = "Недопустимый переход между статусами"
