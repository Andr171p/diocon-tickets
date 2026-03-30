import pytest
from sqlalchemy.exc import IntegrityError

from src.shared.infra.repos import SqlAlchemyRepository

from ..helpers import TestEntity, TestMapper, TestOrm


class SqlTestRepository(SqlAlchemyRepository):
    model = TestOrm
    model_mapper = TestMapper


@pytest.fixture
def test_repo(session):
    return SqlTestRepository(session)


@pytest.fixture
def sample_entity():
    return TestEntity(value="sample-value")


class TestSqlAlchemyRepository:
    @pytest.mark.asyncio
    async def test_create_success(self, session, test_repo, sample_entity):
        created_entity = await test_repo.create(sample_entity)
        await session.commit()

        assert isinstance(created_entity, TestEntity)
        assert created_entity.value == sample_entity.value
        assert created_entity.id == sample_entity.id
        assert created_entity.created_at == sample_entity.created_at
        assert created_entity.updated_at == sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_create_failure_raises_integrity_error(self, session, test_repo):
        entity1 = TestEntity(value="some-value")
        entity2 = TestEntity(value="some-value")
        entity2.id = entity1.id

        await test_repo.create(entity1)
        await session.commit()
        await test_repo.create(entity2)

        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_create_and_read_success(self, session, test_repo, sample_entity):
        await test_repo.create(sample_entity)
        await session.commit()
        entity = await test_repo.read(sample_entity.id)

        assert isinstance(entity, TestEntity)
        assert entity.id == sample_entity.id
        assert entity.value == sample_entity.value
        assert entity.created_at == sample_entity.created_at
        assert entity.updated_at == sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_read_returns_none(self, test_repo, sample_entity):
        entity = await test_repo.read(sample_entity.id)

        assert entity is None

    @pytest.mark.asyncio
    async def test_create_and_update_success(self, session, test_repo, sample_entity):
        await test_repo.create(sample_entity)
        await session.commit()
        updated_entity = await test_repo.update(sample_entity.id, value="updated-value")

        assert isinstance(updated_entity, TestEntity)
        assert updated_entity.id == sample_entity.id
        assert updated_entity.value == "updated-value"
        assert updated_entity.created_at == sample_entity.created_at
        assert updated_entity.updated_at != sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_update_returns_none(self, test_repo, sample_entity):
        entity = await test_repo.update(sample_entity.id, value="updated-value")

        assert entity is None

    @pytest.mark.asyncio
    async def test_create_and_upsert_success(self, session, test_repo, sample_entity):
        await test_repo.create(sample_entity)
        await session.commit()

        sample_entity.value = "refreshed-value"
        await test_repo.upsert(sample_entity)
        await session.commit()

        entity = await test_repo.read(sample_entity.id)

        assert isinstance(entity, TestEntity)
        assert entity.id == sample_entity.id
        assert entity.value == "refreshed-value"
        assert entity.created_at == sample_entity.created_at
        assert entity.updated_at != sample_entity.updated_at

    @pytest.mark.asyncio
    async def test_create_and_delete_success(self, session, test_repo, sample_entity):
        await test_repo.create(sample_entity)
        await session.commit()

        entity = await test_repo.read(sample_entity.id)

        assert isinstance(entity, TestEntity)

        await test_repo.delete(sample_entity.id)
        await session.commit()

        entity = await test_repo.read(sample_entity.id)

        assert entity is None
