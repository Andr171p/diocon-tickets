from .domain.entities import Counterparty
from .schemas import ContactPersonOut, CounterpartyResponse


def map_counterparty_to_response(counterparty: Counterparty) -> CounterpartyResponse:
    """
    Преобразование доменной сущности контрагента к API схеме ответа
    """

    return CounterpartyResponse(
        id=counterparty.id,
        created_at=counterparty.created_at,
        updated_at=counterparty.updated_at,
        counterparty_type=counterparty.counterparty_type,
        name=counterparty.name,
        legal_name=counterparty.legal_name,
        inn=f"{counterparty.inn}",
        kpp=f"{counterparty.kpp}",
        okpo=f"{counterparty.okpo}",
        phone=f"{counterparty.phone}",
        email=counterparty.email,
        address=counterparty.address,
        avatar_url=counterparty.avatar_url,
        is_master=counterparty.is_master,
        parent_id=counterparty.parent_id,
        is_slave=counterparty.is_slave,
        is_active=counterparty.is_active,
        contact_person=(
            None
            if counterparty.contact_person is None
            else ContactPersonOut(
                full_name=f"{counterparty.contact_person.full_name}",
                phone=f"{counterparty.contact_person.phone}",
                email=counterparty.contact_person.email,
                messengers=counterparty.contact_person.messengers,
            )
        ),
    )
