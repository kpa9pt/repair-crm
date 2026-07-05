# tests/api/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


from services.gateway.app.main import app
from services.auth.app.main import app as auth_app


# ============================================================
# 1. КЛИЕНТЫ
# ============================================================


@pytest_asyncio.fixture
async def client():
    """Клиент для Gateway API"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client():
    """Клиент для Auth Service"""
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test/auth") as ac:
        yield ac


# ============================================================
# 2. СБРОС БД (как было)
# ============================================================


@pytest_asyncio.fixture(autouse=True)
async def reset():
    """Сброс состояния БД перед каждым тестом"""
    from shared.db.session import reset_db

    reset_db()


# ============================================================
# 3. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ (исправленная версия)
# ============================================================


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_users():
    """
    Создает admin и instructor в test БД.
    Выполняется один раз перед всеми тестами.
    """
    from shared import get_session_maker
    from shared.auth import get_password_hash
    from shared.models import User
    from sqlalchemy import select

    session_maker = get_session_maker()

    async with session_maker() as session:
        # Проверяем и создаем admin
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
            )
            session.add(admin)
            print("✅ Admin created")

        # Проверяем и создаем instructor
        result = await session.execute(
            select(User).where(User.username == "instructor1")
        )
        instructor = result.scalar_one_or_none()
        if not instructor:
            instructor = User(
                username="instructor1",
                password_hash=get_password_hash("pass123"),
                role="instructor",
            )
            session.add(instructor)
            print("✅ Instructor created")

        await session.commit()

    yield  # Тесты выполняются


# ============================================================
# 4. ТОКЕНЫ (просто берут существующих пользователей)
# ============================================================


@pytest_asyncio.fixture
async def admin_token(auth_client):
    """Получить токен admin"""
    response = await auth_client.post(
        "/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def instructor_token(auth_client):
    """Получить токен instructor"""
    response = await auth_client.post(
        "/login",
        json={"username": "instructor1", "password": "pass123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


# ============================================================
# 5. АВТОРИЗОВАННЫЕ КЛИЕНТЫ
# ============================================================


@pytest_asyncio.fixture
async def authed_client(client, admin_token):
    """Gateway клиент с авторизацией (админ)"""
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return client


@pytest_asyncio.fixture
async def instructor_client(client, instructor_token):
    """Gateway клиент с авторизацией (инструктор)"""
    client.headers.update({"Authorization": f"Bearer {instructor_token}"})
    return client
