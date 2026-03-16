from datetime import datetime, timedelta

from ..settings import timezone


def current_datetime() -> datetime:
    """Получение текущего времени"""

    return datetime.now(timezone)


def get_expiration_timestamp(expires_in: timedelta) -> int:
    """Получение и расчёт Unix Timestamp для истечения времени"""

    return int((current_datetime() + expires_in).timestamp())
