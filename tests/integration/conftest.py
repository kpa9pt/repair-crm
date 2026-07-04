"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from shared.db.session import reset_db

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="function")  # ← меняем session → function
async def test_engine():
    """Тестовый движок БД (новый для каждого теста)"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        # Важно для asyncpg
        pool_pre_ping=True,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with async_session_maker() as session:
        yield session
        # Откатываем все изменения после теста
        await session.rollback()
