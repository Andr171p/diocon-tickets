import uuid

import pytest

from src.counterparties.domain.entities import Counterparty
from src.counterparties.domain.vo import ContactPerson, CounterpartyType, Inn, Kpp, Okpo, Phone
from src.counterparties.infra.models import CounterpartyOrm
from src.counterparties.infra.repos import CounterpartyMapper
from src.iam.domain.vo import FullName
from src.shared.utils.time import current_datetime


@pytest.fixture
def sample_uuid():
    return uuid.uuid4()


@pytest.fixture
def sample_datetime():
    return current_datetime()


@pytest.fixture
def sample_counterparty_orm(sample_uuid, sample_datetime):
    return CounterpartyOrm(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn="7707083893",
        kpp="773301001",
        okpo="00123456",
        phone="+79991234567",
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_person={
            "full_name": "Петрова Анна Сергеевна",
            "phone": "+79991234567",
            "email": "anna.petrovna@romashka.ru",
            "messengers": {"telegram": "@anna_p", "whatsapp": "+79991234567"}
        },
        is_active=True,
    )


@pytest.fixture
def sample_counterparty_entity(sample_uuid, sample_datetime):
    return Counterparty(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        okpo=Okpo("00123456"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_person=ContactPerson(
            full_name=FullName("Петрова Анна Сергеевна"),
            phone=Phone("+79991234567"),
            email="anna.petrovna@romashka.ru",
            messengers={"telegram": "@anna_p", "whatsapp": "+79991234567"}
        ),
        is_active=True,
    )


def test_to_entity_full_mapping(sample_counterparty_orm):
    """Проверка полного преобразование из ORM в доменную сущность"""

    entity = CounterpartyMapper.to_entity(sample_counterparty_orm)

    assert entity.id == sample_counterparty_orm.id
    assert entity.created_at == sample_counterparty_orm.created_at
    assert entity.updated_at == sample_counterparty_orm.updated_at
    assert entity.counterparty_type == sample_counterparty_orm.counterparty_type
    assert entity.name == sample_counterparty_orm.name
    assert entity.legal_name == sample_counterparty_orm.legal_name
    assert entity.inn.value == sample_counterparty_orm.inn
    assert entity.kpp.value == sample_counterparty_orm.kpp
    assert entity.okpo.value == sample_counterparty_orm.okpo
    assert entity.phone.value == sample_counterparty_orm.phone
    assert entity.email == sample_counterparty_orm.email
    assert entity.address == sample_counterparty_orm.address
    assert entity.avatar_url == sample_counterparty_orm.avatar_url
    assert entity.is_active == sample_counterparty_orm.is_active

    # Проверка контактного лица
    assert entity.contact_person is not None
    assert entity.contact_person.full_name == "Петрова Анна Сергеевна"
    assert entity.contact_person.phone.value == sample_counterparty_orm.contact_person["phone"]
    assert entity.contact_person.email == sample_counterparty_orm.contact_person["email"]
    assert entity.contact_person.messengers == sample_counterparty_orm.contact_person["messengers"]


def test_to_entity_null_fields(sample_uuid, sample_datetime):

    orm = CounterpartyOrm(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
        name="Иванов Иван Иванович",
        legal_name="Иванов И.И. (ИП)",
        inn="500100732259",
        kpp=None,
        okpo=None,
        phone="+79991234567",
        email="ivanov@example.com",
        address=None,
        avatar_url=None,
        contact_person=None,
        is_active=False,
    )

    entity = CounterpartyMapper.to_entity(orm)

    assert entity.kpp is None
    assert entity.okpo is None
    assert entity.address is None
    assert entity.avatar_url is None
    assert entity.contact_person is None


def test_from_entity_full_mapping(sample_counterparty_entity):

    orm = CounterpartyMapper.from_entity(sample_counterparty_entity)

    assert orm.id == sample_counterparty_entity.id
    assert orm.created_at == sample_counterparty_entity.created_at
    assert orm.updated_at == sample_counterparty_entity.updated_at
    assert orm.counterparty_type == sample_counterparty_entity.counterparty_type
    assert orm.name == sample_counterparty_entity.name
    assert orm.legal_name == sample_counterparty_entity.legal_name
    assert orm.inn == sample_counterparty_entity.inn.value
    assert orm.kpp == sample_counterparty_entity.kpp.value
    assert orm.okpo == sample_counterparty_entity.okpo.value
    assert orm.phone == sample_counterparty_entity.phone.value
    assert orm.email == sample_counterparty_entity.email
    assert orm.address == sample_counterparty_entity.address
    assert orm.avatar_url == sample_counterparty_entity.avatar_url
    assert orm.is_active == sample_counterparty_entity.is_active

    assert orm.contact_person is not None
    assert orm.contact_person["full_name"] == (
        sample_counterparty_entity.contact_person.full_name.value
    )
    assert orm.contact_person["phone"] == sample_counterparty_entity.contact_person.phone.value
    assert orm.contact_person["email"] == sample_counterparty_entity.contact_person.email
    assert orm.contact_person["messengers"] == sample_counterparty_entity.contact_person.messengers


def test_from_entity_null_contact_person(sample_uuid, sample_datetime):

    entity = Counterparty(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        okpo=Okpo("00123456"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_person=None,
        is_active=True,
    )

    orm = CounterpartyMapper.from_entity(entity)

    assert orm.contact_person is None


def test_round_trip_consistency(sample_counterparty_orm):

    entity = CounterpartyMapper.to_entity(sample_counterparty_orm)
    orm_back = CounterpartyMapper.from_entity(entity)

    assert orm_back.id == sample_counterparty_orm.id
    assert orm_back.counterparty_type == sample_counterparty_orm.counterparty_type
    assert orm_back.name == sample_counterparty_orm.name
    assert orm_back.legal_name == sample_counterparty_orm.legal_name
    assert orm_back.inn == sample_counterparty_orm.inn
    assert orm_back.kpp == sample_counterparty_orm.kpp
    assert orm_back.okpo == sample_counterparty_orm.okpo
    assert orm_back.phone == sample_counterparty_orm.phone
    assert orm_back.email == sample_counterparty_orm.email
    assert orm_back.address == sample_counterparty_orm.address
    assert orm_back.avatar_url == sample_counterparty_orm.avatar_url

    if orm_back.contact_person and sample_counterparty_orm.contact_person:
        assert orm_back.contact_person["full_name"] == (
            sample_counterparty_orm.contact_person["full_name"]
        )
        assert orm_back.contact_person["phone"] == sample_counterparty_orm.contact_person["phone"]
        assert orm_back.contact_person["email"] == sample_counterparty_orm.contact_person["email"]
