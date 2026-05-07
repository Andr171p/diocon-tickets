from uuid import uuid4

import pytest

from src.iam.domain.services import (
    PermissionResult,
    create_customer,
    create_support,
    get_display_user_role,
    invite_customer,
    invite_support,
)
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError

TEST_PASSWORD_HASH = "hash"


def test_permission_result_requires_reason_when_not_allowed():
    """
    Проверяем PermissionResult: он нужен, чтобы запрещающий результат всегда
    объяснял причину отказа.
    Данные: allowed=False без reason.
    """
    with pytest.raises(ValueError, match="Reason required"):
        PermissionResult(allowed=False, reason=None)


def test_permission_result_allows_false_with_reason():
    """
    Проверяем PermissionResult: он должен разрешать запрещающий результат,
    если причина отказа явно передана.
    Данные: allowed=False и reason='denied'.
    """
    result = PermissionResult(allowed=False, reason="denied")

    assert result.allowed is False
    assert result.reason == "denied"


def test_create_customer_raises_for_support_role():
    """
    Проверяем доменную фабрику customer-пользователя: она нужна, чтобы
    не создать клиента с ролью сотрудника поддержки.
    Данные: email, hash, counterparty_id и роль SUPPORT_AGENT.
    """
    with pytest.raises(InvariantViolationError, match="Invalid role chosen for customer"):
        create_customer(
            email="customer@example.com",
            password_hash=TEST_PASSWORD_HASH,
            counterparty_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )


def test_create_support_raises_for_non_support_role():
    """
    Проверяем доменную фабрику support-пользователя: она нужна, чтобы
    не создать сотрудника поддержки с клиентской ролью.
    Данные: email, hash и роль CUSTOMER.
    """
    with pytest.raises(InvariantViolationError, match="Invalid role chosen for support"):
        create_support(
            email="support@example.com",
            password_hash=TEST_PASSWORD_HASH,
            user_role=UserRole.CUSTOMER,
        )


def test_invite_support_raises_for_invalid_role():
    """
    Проверяем доменную фабрику support-приглашения: она нужна, чтобы
    приглашение сотрудника поддержки не получило клиентскую роль.
    Данные: invited_by, email и роль CUSTOMER.
    """
    with pytest.raises(InvariantViolationError, match="Invalid role assignment for support"):
        invite_support(
            invited_by=uuid4(),
            email="support@example.com",
            assigned_role=UserRole.CUSTOMER,
        )


def test_invite_customer_raises_for_invalid_role():
    """
    Проверяем доменную фабрику customer-приглашения: она нужна, чтобы
    приглашение клиента не получило роль сотрудника поддержки.
    Данные: invited_by, email, counterparty_id и роль SUPPORT_MANAGER.
    """
    with pytest.raises(InvariantViolationError, match="Invalid role assignment for customer"):
        invite_customer(
            invited_by=uuid4(),
            email="customer@example.com",
            counterparty_id=uuid4(),
            assigned_role=UserRole.SUPPORT_MANAGER,
        )


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.CUSTOMER, "Клиент"),
        (UserRole.CUSTOMER_ADMIN, "Клиент"),
        (UserRole.SUPPORT_AGENT, "Сотрудник поддержки"),
        (UserRole.SUPPORT_MANAGER, "Сотрудник поддержки"),
        (UserRole.ADMIN, "Администратор"),
    ],
)
def test_get_display_user_role(role, expected):
    """
    Проверяем отображение роли пользователя: оно нужно, чтобы доменная роль
    превращалась в понятный текст для UI.
    Данные: каждая роль UserRole и ожидаемая строка отображения.
    """
    assert get_display_user_role(role) == expected
