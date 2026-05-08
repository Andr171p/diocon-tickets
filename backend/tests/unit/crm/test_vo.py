import pytest

from src.crm.domain.vo import ContactPerson, Inn, Kpp, Okpo, Phone
from src.iam.domain.vo import FullName


@pytest.mark.parametrize(
    ("valid_input", "expected_normalized", "expected_str"),
    [
        ("7707083893", "7707083893", "7707 083893"),
        ("  7 7 0 7 0 8 3 8 9 3  ", "7707083893", "7707 083893"),
        ("500100732259", "500100732259", "5001 0073 2259"),
        ("  5 0 0 1 0 0 7 3 2 2 5 9  ", "500100732259", "5001 0073 2259"),
        ("7707-0838-93", "7707083893", "7707 083893"),
    ]
)
def test_inn_valid_cases(valid_input, expected_normalized, expected_str):
    """Тест для валидного представления ИНН"""

    inn = Inn(valid_input)
    assert inn.value == expected_normalized
    assert str(inn) == expected_str
    assert repr(inn).startswith("Inn(")


@pytest.mark.parametrize(
    ("invalid_input", "expected_error_substr"),
    [
        ("", "INN can contains only digits"),
        ("123", "INN must contain 10 or 12 digits"),
        ("770708389", "INN must contain 10 or 12 digits"),
        ("77070838933", "INN must contain 10 or 12 digits"),
        ("770708389a", "INN can contains only digits"),
        ("  abcdefghij  ", "INN can contains only digits"),
    ]
)
def test_inn_invalid_cases(invalid_input, expected_error_substr):
    """Тест для некорректного ввода ИНН"""

    with pytest.raises(ValueError) as exc:  # noqa: PT011
        Inn(invalid_input)

    assert expected_error_substr.lower() in str(exc.value).lower()


def test_inn_properties():
    """Проверка свойств ИНН для юр.лиц и ИП"""

    legal = Inn("7707083893")
    assert legal.is_legal_entity is True
    assert legal.is_individual is False

    individual = Inn("500100732259")
    assert individual.is_legal_entity is False
    assert individual.is_individual is True


@pytest.mark.parametrize(
    ("valid_input", "expected_normalized", "expected_str"),
    [
        ("773301001", "773301001", "7733/01/001"),
        ("  7 7 3 3 0 1 0 0 1  ", "773301001", "7733/01/001"),
        ("540601001", "540601001", "5406/01/001"),
    ]
)
def test_kpp_valid_cases(valid_input, expected_normalized, expected_str):
    kpp = Kpp(valid_input)
    assert kpp.value == expected_normalized
    assert str(kpp) == expected_str


@pytest.mark.parametrize(
    ("invalid_input", "expected_error_substr"),
    [
        ("", "KPP must contains only digits"),
        ("12345678", "KPP must contain exactly 9 digits"),
        ("1234567890", "KPP must contain exactly 9 digits"),
        ("77330100A", "KPP must contains only digits"),
    ]
)
def test_kpp_invalid_cases(invalid_input, expected_error_substr):
    with pytest.raises(ValueError) as exc:  # noqa: PT011
        Kpp(invalid_input)

    assert expected_error_substr.lower() in str(exc.value).lower()


@pytest.mark.parametrize(
    ("valid_input", "expected_normalized"),
    [
        ("00123456", "00123456"),
        ("1234567890", "1234567890"),
        ("  0 0 1 2 3 4 5 6  ", "00123456"),
        ("9876543210", "9876543210"),
    ]
)
def test_okpo_valid_cases(valid_input, expected_normalized):
    okpo = Okpo(valid_input)
    assert okpo.value == expected_normalized
    assert str(okpo) == expected_normalized


@pytest.mark.parametrize(
    ("invalid_input", "expected_error_substr"),
    [
        ("", "OKPO must contains only digits"),
        ("1234567", "OKPO must contains 8 or 10 digits"),
        ("123456789", "OKPO must contains 8 or 10 digits"),
        ("12345678901", "OKPO must contains 8 or 10 digits"),
        ("0012345A", "OKPO must contains only digits"),
    ]
)
def test_okpo_invalid_cases(invalid_input, expected_error_substr):
    with pytest.raises(ValueError) as exc:  # noqa: PT011
        Okpo(invalid_input)

    assert expected_error_substr.lower() in str(exc.value).lower()


def test_okpo_properties():
    legal = Okpo("00123456")
    assert legal.is_legal_entity is True
    assert legal.is_individual_or_branch is False

    ip = Okpo("1234567890")
    assert ip.is_legal_entity is False
    assert ip.is_individual_or_branch is True


@pytest.mark.parametrize(
    ("input_phone", "expected_normalized", "expected_str"),
    [
        ("+79991234567", "+79991234567", "+7 (999) 123-45-67"),
        ("89991234567", "+79991234567", "+7 (999) 123-45-67"),
        ("9 999 123 45 67", "+79991234567", "+7 (999) 123-45-67"),
        ("+7 (999) 123-45-67", "+79991234567", "+7 (999) 123-45-67"),
        ("8 (999) 123 45 67", "+79991234567", "+7 (999) 123-45-67"),
        ("9991234567", "+79991234567", "+7 (999) 123-45-67"),
    ]
)
def test_phone_valid_normalization(input_phone, expected_normalized, expected_str):
    phone = Phone(input_phone)
    assert phone.value == expected_normalized
    assert str(phone) == expected_str


@pytest.mark.parametrize(
    ("invalid_phone", "expected_error_substr"),
    [
        ("", "cannot be empty"),
        ("abc", "cannot be empty"),
        ("899912345678", "Invalid phone number"),
        ("+1 555 1234567", "Invalid phone number"),
        ("+79991234abc", "Invalid phone number"),
    ]
)
def test_phone_invalid_cases(invalid_phone, expected_error_substr):
    with pytest.raises(ValueError) as exc:  # noqa: PT011
        Phone(invalid_phone)

    assert expected_error_substr.lower() in str(exc.value).lower()


def test_phone_equality():
    first_phone = Phone("+79991234567")
    second_phone = Phone("89991234567")
    third_phone = Phone("  +7  (999)  123  45  67  ")

    assert first_phone == second_phone
    assert first_phone == third_phone
    assert hash(first_phone) == hash(second_phone) == hash(third_phone)


def test_kpp_repr():
    """
    Проверяем repr для Kpp: он нужен для понятного отображения value object
    в отладке и сообщениях тестов.
    Данные: валидный КПП.
    """
    kpp = Kpp("773301001")

    assert repr(kpp) == "Kpp('773301001')"


def test_okpo_repr():
    """
    Проверяем repr для Okpo: он нужен для понятного отображения value object
    в отладке и сообщениях тестов.
    Данные: валидный ОКПО.
    """
    okpo = Okpo("00123456")

    assert repr(okpo) == "Okpo('00123456')"


def test_phone_invalid_length_after_normalization():
    """
    Проверяем телефон: он должен упасть, если после нормализации длина
    не соответствует формату +7 и 10 цифр.
    Данные: номер, который начинается с 9, но содержит слишком мало цифр.
    """
    with pytest.raises(ValueError, match="Invalid phone number"):
        Phone("912345678")


def test_phone_repr():
    """
    Проверяем repr для Phone: он нужен для понятного отображения телефона
    в отладке и сообщениях тестов.
    Данные: валидный телефон.
    """
    phone = Phone("+79991234567")

    assert repr(phone) == "Phone('+79991234567')"


def test_contact_person_raises_for_disabled_messenger():
    """
    Проверяем ContactPerson: он должен отказать, если передан мессенджер
    не из разрешенного списка.
    Данные: контактное лицо с messenger discord.
    """
    with pytest.raises(ValueError, match="Disabled messengers"):
        ContactPerson(
            full_name=FullName("Иванов Иван Иванович"),
            phone=Phone("+79991234567"),
            email="ivan@example.com",
            messengers={"discord": "ivan"},
        )


@pytest.mark.parametrize("bad_value", ["", None, 123])
def test_contact_person_raises_for_empty_or_not_string_messenger_value(bad_value):
    """
    Проверяем ContactPerson: значение messenger должно быть непустой строкой.
    Данные: telegram со значением пустая строка, None или число.
    """
    with pytest.raises(ValueError, match="must be non empty string"):
        ContactPerson(
            full_name=FullName("Иванов Иван Иванович"),
            phone=Phone("+79991234567"),
            email="ivan@example.com",
            messengers={"telegram": bad_value},
        )


def test_contact_person_repr():
    """
    Проверяем repr для ContactPerson: он нужен для понятного отображения
    контактного лица в отладке и сообщениях тестов.
    Данные: валидное контактное лицо с telegram.
    """
    contact_person = ContactPerson(
        full_name=FullName("Иванов Иван Иванович"),
        phone=Phone("+79991234567"),
        email="ivan@example.com",
        messengers={"telegram": "ivan"},
    )

    assert repr(contact_person) == (
        "ContactPerson("
        "full_name=FullName('Иванов Иван Иванович'), "
        "phone=Phone('+79991234567'), "
        "email='ivan@example.com', "
        "messengers={'telegram': 'ivan'})"
    )
