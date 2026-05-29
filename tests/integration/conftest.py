"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД (один раз на сессию)"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
