import pytest

from src.tickets.domain.vo import ProjectKey


class TestProjectKey:

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("prj", "PRJ"),
            ("  mOb_App  ", "MOB_APP"),
            ("Backend1", "BACKEND1"),
            ("ПРОЕКТ", "ПРОЕКТ"),
            ("A1", "A1"),
            ("A_" * 5, "A_" * 5),
            ("project", "PROJECT"),
        ],
    )
    def test_should_create_valid_key_and_normalize(self, raw, expected):
        key = ProjectKey(raw)
        assert key.value == expected
        assert str(key) == expected
        assert repr(key) == f"ProjectKey('{expected}')"

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "A",  # слишком короткий (1 символ)
            "A" * 11,  # слишком длинный (11 символов)
            "1PROJ",  # начинается с цифры
            "_PROJ",  # начинается с подчёркивания
            "PROJ-1",  # содержит дефис
            "PRO J",  # содержит пробел
            "PROJ!",  # содержит спецсимвол
            "PROJ.",  # содержит точку
            "абвгдежзикл",  # 11 символов
        ],
    )
    def test_should_raise_error_for_invalid_key(self, invalid_key):
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey(invalid_key)

    def test_should_raise_error_for_empty_string(self):
        with pytest.raises(ValueError, match="Project key cannot be empty"):
            ProjectKey("")

    def test_should_raise_error_for_too_long_key(self):
        long_key = "A" * 11
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey(long_key)

    def test_should_raise_error_for_too_short_key(self):
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey("X")  # 1 символ

    def test_should_raise_error_when_first_char_not_letter(self):
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey("123")

    def test_should_raise_error_when_contains_disallowed_symbols(self):
        with pytest.raises(ValueError, match="Invalid project key format"):
            ProjectKey("HELLO-WORLD")

    def test_should_strip_whitespace_and_uppercase(self):
        key = ProjectKey("   test_key   ")
        assert key.value == "TEST_KEY"

    def test_should_accept_underscore_and_digits(self):
        key = ProjectKey("PROJ_123")
        assert key.value == "PROJ_123"
