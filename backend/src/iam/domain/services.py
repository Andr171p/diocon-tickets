from datetime import timedelta
from uuid import UUID

from pydantic import SecretStr

from ...shared.domain.exceptions import InvariantViolationError
from ...shared.utils.time import get_expiration_time
from .entities import Invitation, User
from .vo import FullName, Username, UserRole

INVITATION_EXPIRES_IN_DAYS = 7


def create_customer(
    email: str,
    password_hash: str,
    counterparty_id: UUID,
    user_role: UserRole = UserRole.CUSTOMER,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    """Создание клиента - тот кто публикует тикеты"""

    if user_role in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER}:
        raise InvariantViolationError("Invalid role chosen for customer")
    return User(
        email=email,
        password_hash=SecretStr(password_hash),
        counterparty_id=counterparty_id,
        username=None if username is None else Username(username),
        full_name=None if full_name is None else FullName(full_name),
        role=user_role,
    )


def create_support(
    email: str,
    password_hash: str,
    user_role: UserRole = UserRole.SUPPORT_AGENT,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    """Создание агента поддержки - тот кто получает тикеты и назначает их исполнителям"""

    if user_role not in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER}:
        raise InvariantViolationError("Invalid role chosen for support")

    return User(
        email=email,
        password_hash=SecretStr(password_hash),
        username=None if username is None else Username(username),
        full_name=None if full_name is None else FullName(full_name),
        role=user_role,
    )


def create_admin(email: str, password_hash: str) -> User:
    """Фабрика для создания системного администратора"""

    return User(
        email=email,
        password_hash=SecretStr(password_hash),
        username=Username("admin"),
        role=UserRole.ADMIN,
    )


def invite_support(
        invited_by: UUID, email: str, assigned_role: UserRole
) -> Invitation:
    """Создание приглашения для сотрудника поддержки"""

    if assigned_role not in {UserRole.SUPPORT_MANAGER, UserRole.SUPPORT_AGENT}:
        raise InvariantViolationError("Invalid role assignment for support")

    return Invitation(
        email=email,
        invited_by=invited_by,
        assigned_role=assigned_role,
        expires_at=get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS)),
    )


def invite_customer(
        invited_by: UUID, email: str, counterparty_id: UUID, assigned_role: UserRole
) -> Invitation:
    """Создание приглашения для клиента"""

    if assigned_role not in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN}:
        raise InvariantViolationError("Invalid role assignment for customer")

    return Invitation(
        email=email,
        invited_by=invited_by,
        counterparty_id=counterparty_id,
        assigned_role=assigned_role,
        expires_at=get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS)),
    )
