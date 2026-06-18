from typing import Any, Protocol

from dataclasses import dataclass, field
from enum import StrEnum, auto
from uuid import UUID


class PrincipalType(StrEnum):
    USER = auto()  # пользователь (человек)
    CLIENT = auto()  # внешние интеграции (machine 2 machine)
    AI_AGENT = auto()


@dataclass(frozen=True, kw_only=True)
class Principal:
    """
    Единый субъект авторизации в системе.
    Объединяет как обычных пользователей, так и внешние приложения.
    """

    id: UUID
    type: PrincipalType

    scopes: list[str] = field(default_factory=list)  # для clients

    roles: list[str] = field(default_factory=list)
    counterparty_id: UUID | None = None
    is_active: bool

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_user(self) -> bool:
        return self.type == PrincipalType.USER

    @property
    def is_client(self) -> bool:
        return self.type == PrincipalType.CLIENT

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass(frozen=True)
class PermissionResult:
    allowed: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.allowed and self.reason is None:
            raise ValueError("Reason required, when not allowed")


class AuthorizationRule[AuthContextT](Protocol):
    """
    Атомарное правило проверки прав доступа.
    Каждое правило реализует ровно один бизнес инвариант или условие безопасности.
    """

    @staticmethod
    def check(ctx: AuthContextT) -> PermissionResult: ...


class AllOf[AuthContextT]:
    """
    Стратегия при которой ВСЕ правила должны выполниться.
    Возвращает первую возникшую ошибку (важен порядок).
    """

    def __init__(self, *rules: AuthorizationRule[AuthContextT]) -> None:
        self._rules = rules

    def check(self, ctx: AuthContextT) -> PermissionResult:
        for rule in self._rules:
            permission = rule.check(ctx)
            if not permission.allowed:
                return permission

        return PermissionResult(True)


class AnyOf[AuthContextT]:
    """
    Стратегия при которой должно выполниться ХОТЯ БЫ ОДНО правило.
    Возвращает ошибку, если не выполнилось ни одно условие (копит ошибки).
    Важен порядок, так как выводится последнее сообщение об ошибке.
    """

    def __init__(self, *rules: AuthorizationRule[AuthContextT]) -> None:
        self._rules = rules

    def check(self, ctx: AuthContextT) -> PermissionResult:
        reasons: list[str] = []

        for rule in self._rules:
            permission = rule.check(ctx)
            if permission.allowed:
                return permission

            reasons.append(permission.reason)

        final_reason = reasons[-1] if reasons else "Access denied"
        return PermissionResult(False, final_reason)


@dataclass(frozen=True)
class BaseAuthContext:
    principal: Principal
