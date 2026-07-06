# tests/api/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from shared.settings import get_settings  # ← ДОБАВИТЬ

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
# 2. СБРОС БД
# ============================================================
@pytest_asyncio.fixture(autouse=True)
async def reset():
    """Сброс состояния БД перед каждым тестом"""
    from shared.db.session import reset_db

    reset_db()


# ============================================================
# 3. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ (ИЗ .ENV!)
# ============================================================
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_users():
    """
    Создает admin и instructor в test БД.
    Берет пароли из .env (через get_settings()).
    """
    from shared import get_session_maker
    from shared.auth import get_password_hash
    from shared.models import User
    from sqlalchemy import select

    settings = get_settings()  # ← ДОБАВИТЬ ЭТУ СТРОКУ!

    session_maker = get_session_maker()

    async with session_maker() as session:
        # ---------- ADMIN ----------
        result = await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
        admin = result.scalar_one_or_none()

        if admin:
            # Если есть — обновляем пароль из .env
            admin.password_hash = get_password_hash(settings.admin_password)
            print(f"✅ Admin password updated to: {settings.admin_password}")
        else:
            # Если нет — создаем
            admin = User(
                username=settings.admin_username,
                password_hash=get_password_hash(settings.admin_password),
                role="admin",
            )
            session.add(admin)
            print(f"✅ Admin created with password: {settings.admin_password}")

        # ---------- INSTRUCTOR ----------
        instructor_password = "pass123"

        result = await session.execute(
            select(User).where(User.username == "instructor1")
        )
        instructor = result.scalar_one_or_none()

        if instructor:
            instructor.password_hash = get_password_hash(instructor_password)
            print(f"✅ Instructor password updated to: {instructor_password}")
        else:
            instructor = User(
                username="instructor1",
                password_hash=get_password_hash(instructor_password),
                role="instructor",
            )
            session.add(instructor)
            print("✅ Instructor created")

        await session.commit()


# ============================================================
# 4. ТОКЕНЫ
# ============================================================
@pytest_asyncio.fixture
async def admin_token(auth_client):
    """Получить токен admin (пароль из .env)"""
    settings = get_settings()
    response = await auth_client.post(
        "/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
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
