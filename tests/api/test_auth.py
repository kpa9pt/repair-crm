import pytest

pytestmark = pytest.mark.asyncio


class TestAuth:
    """Тесты аутентификации"""

    async def test_login_success(self, auth_client):
        """Успешный логин"""
        response = await auth_client.post(
            "/login", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, auth_client):
        """Неверный пароль"""
        response = await auth_client.post(
            "/login", json={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 401

    async def test_me_with_token(self, admin_token, auth_client):
        """Получение информации о себе с токеном"""
        response = await auth_client.get(
            "/me", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert "id" in data

    async def test_me_without_token(self, auth_client):
        """Доступ к /me без токена — 401"""
        response = await auth_client.get("/me")
        assert response.status_code == 401

    async def test_register_as_admin(self, admin_token, auth_client):
        """Регистрация пользователя админом"""
        response = await auth_client.post(
            "/register",
            json={"username": "newuser", "password": "newpass", "role": "instructor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "instructor"

    async def test_register_duplicate_username(self, admin_token, auth_client):
        """Регистрация с уже существующим username — 400"""
        # Сначала создаем пользователя
        await auth_client.post(
            "/register",
            json={
                "username": "duplicate_user",
                "password": "pass",
                "role": "instructor",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Пытаемся создать еще раз
        response = await auth_client.post(
            "/register",
            json={
                "username": "duplicate_user",
                "password": "pass2",
                "role": "instructor",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Username already taken" in response.text

    async def test_register_as_instructor_forbidden(
        self, instructor_token, auth_client
    ):
        """Инструктор не может регистрировать"""
        response = await auth_client.post(
            "/register",
            json={"username": "hacker", "password": "hack", "role": "admin"},
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert response.status_code == 403

    async def test_validate_token_valid(self, auth_client, admin_token):
        """Валидация валидного токена — 200"""
        response = await auth_client.post("/validate", json={"token": admin_token})
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    async def test_validate_token_invalid(self, auth_client):
        """Валидация невалидного токена — 401"""
        response = await auth_client.post(
            "/validate", json={"token": "invalid.token.here"}
        )
        assert response.status_code == 401

    async def test_validate_token_expired(self, auth_client):
        """Валидация просроченного токена — 401"""
        # Создаем токен с истекшим временем
        from shared.auth import create_access_token
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": 1, "username": "admin", "role": "admin"},
            expires_delta=timedelta(seconds=-1),  # уже просрочен
        )

        response = await auth_client.post("/validate", json={"token": expired_token})
        assert response.status_code == 401
