from dataclasses import dataclass
from decimal import Decimal

from ...shared.domain.vo import ValueObject


@dataclass(frozen=True, slots=True)
class NonNegativeDecimal(ValueObject):
    """
    Не отрицательное число (для точных значений: счета, часы, ...)
    """

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(f"{self.value}"))

        if self.value <= 0:
            raise ValueError(f"Value must be positive, got {self.value}")

    def __mul__(self, other) -> "NonNegativeDecimal":
        if isinstance(other, (int, Decimal)):
            return NonNegativeDecimal(self.value * other)

        return NotImplemented

    def __str__(self) -> str:
        return f"{self.value}"
