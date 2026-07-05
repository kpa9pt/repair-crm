"""
Интеграционные тесты полного auth flow
"""

import pytest
from httpx import AsyncClient, ASGITransport
from services.auth.app.main import app

pytestmark = pytest.mark.asyncio


class TestAuthFlow:
    """Тесты полного auth flow"""

    @pytest.fixture
    async def auth_client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test/auth"
        ) as client:
            yield client

    async def test_full_auth_flow(self, auth_client, test_session):
        """Полный flow: создание пользователя → логин → получение профиля"""
        from services.auth.app.repositories.user import UserRepository

        # 1. Создаем админа
        repo = UserRepository(test_session)
        admin = await repo.create(username="admin", password="admin123", role="admin")
        await test_session.commit()
        await test_session.refresh(admin)  # ← ДОБАВИТЬ
        assert admin.id is not None  # ← ДОБАВИТЬ (используем переменную)

        # 2. Логинимся
        login_resp = await auth_client.post(
            "/login", json={"username": "admin", "password": "admin123"}
        )
        assert login_resp.status_code == 200
        admin_token = login_resp.json()["access_token"]

        # 3. Регистрируем нового пользователя
        register_resp = await auth_client.post(
            "/register",
            json={
                "username": "newuser",
                "password": "newpass123",
                "role": "instructor",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert register_resp.status_code == 200
        user_data = register_resp.json()
        assert user_data["username"] == "newuser"

        # 4. Логинимся как новый пользователь
        login_resp = await auth_client.post(
            "/login", json={"username": "newuser", "password": "newpass123"}
        )
        assert login_resp.status_code == 200
        user_token = login_resp.json()["access_token"]

        # 5. Получаем профиль
        me_resp = await auth_client.get(
            "/me", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["username"] == "newuser"
        assert me_data["role"] == "instructor"
