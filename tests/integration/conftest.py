"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from shared.db.session import reset_db
from sqlalchemy import text  # ← ДОБАВИТЬ ЭТОТ ИМПОРТ

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


# ✅ НОВАЯ ФИКСТУРА: очищает таблицы перед каждым тестом
@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_tables(test_engine):
    """Очищает все таблицы перед каждым тестом"""
    from shared.models import Base

    async with test_engine.begin() as conn:
        # Получаем все таблицы в правильном порядке (с учетом внешних ключей)
        for table in reversed(Base.metadata.sorted_tables):
            try:
                await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
            except Exception as e:
                # Если таблица не существует или другая ошибка — пропускаем
                print(f"⚠️  Could not truncate {table.name}: {e}")

    yield
