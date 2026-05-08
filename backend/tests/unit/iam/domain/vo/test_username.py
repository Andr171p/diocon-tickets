# Тесты для доменного примитива Username (логин пользователя)

import pytest

from src.iam.domain.vo import Username

UNSUPPORTED_USERNAME_COMPARISON_VALUE = 123


@pytest.mark.parametrize(
    ("valid_input", "expected_normalized"),
    [
        ("Alex123", "alex123"),
        ("danil.kolbasenko", "danil.kolbasenko"),
        ("support-lead_42", "support-lead_42"),
        ("  User.Name-2025  ", "user.name-2025"),
        ("ИванПетров", "иванпетров"),
    ]
)
def test_valid_usernames_are_normalized(valid_input: str, expected_normalized: str):
    """Тестирование нормализации введённого username"""

    username = Username(valid_input)
    assert username == expected_normalized


@pytest.mark.parametrize(
    ("invalid_input", "error_substring"),
    [
        ("", "cannot be empty"),
        ("ab", "too short"),
        ("a" * 35, "too long"),
        ("user@name", "can only contains"),
        (".username", "can only contains"),
        ("username.", "can only contains"),
        ("user__name", "can only contains"),
        ("user..name", "can only contains"),
        ("user-name-", "can only contains"),
        ("123456", "cannot contains only digits"),
        ("admin support", "can only contains"),
    ]
)
def test_invalid_usernames_raise_error(invalid_input: str, error_substring: str):
    """Тест для неверно введённого имени"""

    with pytest.raises(ValueError) as exc:  # noqa: PT011
        Username(invalid_input)
    assert error_substring in str(exc.value)


def test_equality_case_insensitive():
    """Тест для проверки чувствительности к регистру"""

    username = Username("SuperUser")
    assert username == "superuser"
    assert username == "  SUPERUSER  "
    assert username != "superuser123"


def test_repr_returns_normalized_username():
    """
    Проверяем repr Username: он нужен, чтобы при отладке объект отображался
    понятным текстом и показывал уже нормализованное значение.
    Данные: username со смешанным регистром.
    """
    username = Username("SuperUser")

    assert repr(username) == "Username('superuser')"


def test_equality_with_unsupported_type_returns_false():
    """
    Проверяем сравнение Username с неподдержанным типом: оно не должно считать
    разные типы равными.
    Данные: Username и число.
    """
    username = Username("superuser")

    assert (username == UNSUPPORTED_USERNAME_COMPARISON_VALUE) is False


def test_hashable():
    """Тест для проверки хешируемости объекта"""

    s = {Username("test"), Username("TEST"), Username("TeSt")}
    assert len(s) == 1
