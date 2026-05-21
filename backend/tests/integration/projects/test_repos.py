from uuid import uuid4

import pytest

from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectKey, ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.schemas import PageParams


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)

def make_project(key: str | None = None, owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name="Test Project {uuid4()}",
        key=key or f"PR{uuid4().hex[:6].upper()}",
        description="Test project",
        created_by=user_id,
    )

@pytest.mark.asyncio
async def test_get_by_key_returns_project(session, project_repo):
    """
    Проверяем SQL-репозитории проектов: он нужен, чтобы сервис мог найти
    проект по уникальному ключу перед созданием или проверкой доступности ключа.
    Данные: реальный Project, сохранённый в PostgreSQL.
    """

    project = make_project(key="TESTKEY")

    await project_repo.create(project)
    await session.commit()

    found = await project_repo.get_by_key(ProjectKey("TESTKEY"))

    assert found is not None
    assert found.id == project.id
    assert found.key == ProjectKey("TESTKEY")


@pytest.mark.asyncio
async def test_get_by_key_returns_none(project_repo):
    """
    Проверяем SQL-репозиторий проектов: если проекта с таким ключом нет, 
    метод должен вернуть None, а не падать с ошибкой.
    Данный: ключ, которого нет в реальной БД.
    """

    found = await project_repo.get_by_key(ProjectKey("UNKNOWN"))

    assert found is None

@pytest.mark.asyncio
async def test_get_existing_keys_returns_only_existing_keys(session, project_repo):
    """
    Проверяем поиск существующих ключей: он нужен для генерации свободных
    вариантов ключа при конфликте уникальности.
    Данные: два проекта в реальной БД и один отсутствующий ключ.
    """

    first_project = make_project(key="EXIST1")
    second_project = make_project(key="EXIST2")

    await project_repo.create(first_project)
    await project_repo.create(second_project)
    await session.commit()

    existing_keys = await project_repo.get_existing_keys(["EXIST1", "EXIST2", "FREEKEY"])

    assert existing_keys == {"EXIST1", "EXIST2"}


@pytest.mark.asyncio
async def test_membership_find_returns_membership(session, project_repo, membership_repo):
    """
    Проверяем SQL-репозиторий участников проекта: он нужен для проверки прав
    пользователя внутри конкретного проекта.
    Данные: проект и учатники проекта с ролью CONTRIBUTOR в реальной БД.
    """

    owner_id = uuid4()
    member_id = uuid4()
    project = make_project(key="MEMBER1", owner_id=owner_id)
    membership = project.create_membership(
        user_id=member_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    found = await membership_repo.find(project.id, member_id)

    assert found is not None
    assert found.id == membership.id
    assert found.project_id == project.id
    assert found.user_id == member_id
    assert found.project_role == ProjectRole.CONTRIBUTOR