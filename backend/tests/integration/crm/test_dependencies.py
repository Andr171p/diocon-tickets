from src.crm.dependencies import get_counterparty_repo, get_counterparty_service
from src.crm.infra.repos import SqlCounterpartyRepository
from src.crm.services import CounterpartyService


def test_get_counterparty_repo_returns_sql_counterparty_repo(session):
    """
    Проверяем DI-функцию get_counterparty_repo: она нужна, чтобы FastAPI получил
    SQL-репозиторий контрагентов с текущей сессией БД.
    Данные: реальная AsyncSession из integration fixture.
    """
    repo = get_counterparty_repo(session)

    assert isinstance(repo, SqlCounterpartyRepository)
    assert repo.session is session


def test_get_counterparty_service_wires_dependencies(session):
    """
    Проверяем DI-функцию get_counterparty_service: она нужна, чтобы FastAPI собрал
    CounterpartyService из сессии и SQL-репозитория.
    Данные: реальная AsyncSession и SqlCounterpartyRepository.
    """
    repo = get_counterparty_repo(session)

    service = get_counterparty_service(session=session, repo=repo)

    assert isinstance(service, CounterpartyService)
    assert service.session is session
    assert service.repository is repo
