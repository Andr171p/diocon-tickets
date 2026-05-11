from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.contracts.domain.entities import ServiceContract
from src.contracts.domain.services import can_create_contract, can_manage_packages, can_view_contract
from src.contracts.domain.vo import ContractStatus, ContractType
from src.contracts.services import ContractService
from src.iam.domain.vo import UserRole


@pytest.fixture
def counterparty_id():
    return uuid4()


@pytest.fixture
def sample_contract(counterparty_id):
    return ServiceContract(
        contract_number="CON-001",
        counterparty_id=counterparty_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        total_hours=Decimal("100"),
        status=ContractStatus.ACTIVE,
        contract_type=ContractType.PREPAID,
        created_by=uuid4(),
    )


@pytest.mark.parametrize("user_role", [UserRole.ACCOUNT_MANAGER, UserRole.ADMIN])
def test_can_create_contract_allowed_for_required_roles(user_role):
    """
    Договор может создавать account manager и admin
    """

    result = can_create_contract(user_role)

    assert result.allowed is True
    assert result.reason is None


@pytest.mark.parametrize(
    "user_role",
    [
        UserRole.CUSTOMER,
        UserRole.CUSTOMER_ADMIN,
        UserRole.SUPPORT_AGENT,
        UserRole.SUPPORT_MANAGER,
        UserRole.FINANCE,
    ],
)
def test_can_create_contract_denied_for_wrong_roles(user_role):
    """
    Остальные роли не могут создавать договор
    """

    result = can_create_contract(user_role)

    assert result.allowed is False
    assert result.reason == "Only account manager or above can create contracts"


@pytest.mark.parametrize(
    "user_role",
    [UserRole.ADMIN, UserRole.ACCOUNT_MANAGER, UserRole.FINANCE, UserRole.SUPPORT_MANAGER],
)
def test_can_view_contract_allowed_for_internal_roles(sample_contract, user_role):
    """
    Внутренние роли могут смотреть договоры
    """

    result = can_view_contract(sample_contract, user_role)

    assert result.allowed is True


@pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
def test_can_view_contract_allowed_for_own_counterparty(sample_contract, counterparty_id, user_role):
    """
    Клиент может смотреть договор своего контрагента
    """

    result = can_view_contract(
        sample_contract,
        user_role=user_role,
        user_counterparty_id=counterparty_id,
    )

    assert result.allowed is True


@pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
def test_can_view_contract_denied_for_other_counterparty(sample_contract, user_role):
    """
    Клиент не может смотреть чужой договор
    """

    result = can_view_contract(
        sample_contract,
        user_role=user_role,
        user_counterparty_id=uuid4(),
    )

    assert result.allowed is False
    assert result.reason == "Customers can view contracts issued to his counterparty"


def test_can_view_contract_denied_for_support_agent(sample_contract):
    """
    Обычный агент поддержки не может смотреть договоры
    """

    result = can_view_contract(sample_contract, UserRole.SUPPORT_AGENT)

    assert result.allowed is False
    assert result.reason == "Insufficient rights to view contracts"


@pytest.mark.parametrize("user_role", [UserRole.ACCOUNT_MANAGER, UserRole.ADMIN])
def test_can_manage_packages_allowed_for_required_roles(user_role):
    """
    Пакетами часов может управлять account manager и admin
    """

    result = can_manage_packages(user_role)

    assert result.allowed is True


@pytest.mark.parametrize(
    "user_role",
    [
        UserRole.CUSTOMER,
        UserRole.CUSTOMER_ADMIN,
        UserRole.SUPPORT_AGENT,
        UserRole.SUPPORT_MANAGER,
        UserRole.FINANCE,
    ],
)
def test_can_manage_packages_denied_for_wrong_roles(user_role):
    """
    Остальные роли не могут управлять пакетами часов
    """

    result = can_manage_packages(user_role)

    assert result.allowed is False
    assert result.reason == "Only account manager or above can manage packages"


def test_contract_service_wires_dependencies():
    """
    Сервис договоров хранит сессию и репозиторий
    """

    session = object()
    repository = object()

    service = ContractService(session=session, repository=repository)

    assert service.session is session
    assert service.repository is repository
