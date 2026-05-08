from decimal import Decimal

import pytest

from src.contracts.domain.vo import (
    ContractStatus,
    ContractType,
    EstimationMethod,
    HoursPackageType,
    NonNegativeDecimal,
)


def test_contract_enums_have_expected_values():
    """
    Проверяем значения enum-ов для договоров
    """

    assert ContractStatus.DRAFT == "draft"
    assert ContractStatus.ACTIVE == "active"
    assert ContractStatus.SUSPENDED == "suspended"
    assert ContractStatus.EXPIRED == "expired"
    assert ContractStatus.COMPLETED == "completed"

    assert ContractType.SUBSCRIPTION == "subscription"
    assert ContractType.PREPAID == "prepaid"
    assert ContractType.TIME_AND_MATERIALS == "time_and_materials"
    assert ContractType.HYBRID == "hybrid"

    assert HoursPackageType.MONTHLY == "monthly"
    assert HoursPackageType.QUARTERLY == "quarterly"
    assert HoursPackageType.YEARLY == "yearly"
    assert HoursPackageType.ONE_TIME == "one_time"

    assert EstimationMethod.MANUAL == "manual"
    assert EstimationMethod.AI == "ai"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("10.5"), Decimal("10.5")),
        ("10.5", Decimal("10.5")),
        (10, Decimal("10")),
        (10.5, Decimal("10.5")),
    ],
)
def test_create_non_negative_decimal_success(value, expected):
    """
    Успешное создание положительного Decimal
    """

    decimal_value = NonNegativeDecimal(value)

    assert decimal_value.value == expected
    assert str(decimal_value) == str(expected)


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1"), 0, "-1"])
def test_non_positive_decimal_raises_error(value):
    """
    Нельзя создать Decimal с нулем или отрицательным значением
    """

    with pytest.raises(ValueError, match="Value must be positive"):
        NonNegativeDecimal(value)


def test_non_negative_decimal_multiply_success():
    """
    Умножение возвращает новый value object
    """

    result = NonNegativeDecimal(Decimal("2.5")) * 2

    assert isinstance(result, NonNegativeDecimal)
    assert result.value == Decimal("5.0")


def test_non_negative_decimal_multiply_by_decimal_success():
    """
    Умножение на Decimal возвращает корректное значение
    """

    result = NonNegativeDecimal(Decimal("2.5")) * Decimal("1.5")

    assert result.value == Decimal("3.75")


def test_non_negative_decimal_multiply_by_wrong_type_raises_error():
    """
    Неподдерживаемый тип не должен умножаться
    """

    with pytest.raises(TypeError):
        NonNegativeDecimal(Decimal("2.5")) * "2"
