from .entities import Invitation, User
from .exceptions import InvitationExpiredError
from .vo import Email, FullName, PasswordHash, Username, UserRole


def create_user_from_invitation(
        invitation: Invitation,
        *,
        password_hash: str,
        username: str | None = None,
        full_name: str | None = None,
) -> User:
    """
    Создаёт пользователя, используя приглашение.
    """

    return User(
        email=invitation.email,
        username=Username(username) if username else None,
        full_name=FullName(full_name) if full_name else None,
        password_hash=PasswordHash(password_hash),
        counterparty_id=invitation.counterparty_id,
        roles=invitation.granted_roles,
    )


def register_new_user(
        *,
        invitation: Invitation,
        password_hash: str,
        username: str | None = None,
        full_name: str | None = None,
) -> User:
    """
    Регистрирует нового пользователя.
    """

    if not invitation.is_valid:
        raise InvitationExpiredError(
            f"Invitation for email `{invitation.email}` expired or already used"
        )

    invitation.mark_as_used()

    return create_user_from_invitation(
        invitation,
        password_hash=password_hash,
        username=username,
        full_name=full_name,
    )


def create_admin(email: Email, password_hash: str) -> User:
    """Фабрика для создания системного администратора"""

    return User(
        email=email,
        password_hash=PasswordHash(password_hash),
        username=Username("admin"),
        roles={UserRole.ADMIN},
    )


def get_display_user_role(user_role: UserRole) -> str:
    """Преобразование роли пользователя к UI-friendly формату"""

    match user_role:
        case UserRole.CUSTOMER | UserRole.CUSTOMER_ADMIN:
            return "Клиент"
        case UserRole.SUPPORT_AGENT | UserRole.SUPPORT_MANAGER:
            return "Сотрудник поддержки"
        case UserRole.ADMIN:
            return "Администратор"
        case UserRole.ACCOUNT_MANAGER:
            return "Менеджер по работе с клиентами"
        case UserRole.FINANCE:
            return "Бухгалтер"
