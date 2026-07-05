"""
Интеграционные тесты для UserRepository
"""

import pytest
from services.auth.app.repositories.user import UserRepository
from shared.auth import verify_password

pytestmark = pytest.mark.asyncio


class TestUserRepository:
    """Тесты репозитория пользователей"""

    async def test_create_user(self, test_session):
        """Создание пользователя"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="testuser", password="testpass123", role="instructor"
        )
        await test_session.commit()
        await test_session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == "instructor"
        assert verify_password("testpass123", user.password_hash)

    async def test_get_by_id(self, test_session):
        """Получение пользователя по ID"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="user_by_id", password="pass123", role="admin"
        )
        await test_session.commit()
        await test_session.refresh(user)

        found = await repo.get_by_id(user.id)
        assert found is not None
        assert found.id == user.id
        assert found.username == "user_by_id"

    async def test_get_by_username(self, test_session):
        """Получение пользователя по username"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="unique_user", password="pass123", role="instructor"
        )
        await test_session.commit()
        await test_session.refresh(user)

        found = await repo.get_by_username("unique_user")
        assert found is not None
        assert found.id == user.id
        assert found.username == "unique_user"

    async def test_authenticate_success(self, test_session):
        """Успешная аутентификация"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="auth_user", password="correct_password", role="instructor"
        )
        await test_session.commit()
        await test_session.refresh(user)
        assert user.id is not None  # ← ДОБАВИТЬ (используем переменную)

        authenticated = await repo.authenticate("auth_user", "correct_password")
        assert authenticated is not None
        assert authenticated.username == "auth_user"

    async def test_authenticate_wrong_password(self, test_session):
        """Аутентификация с неверным паролем"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="auth_user", password="correct_password", role="instructor"
        )
        await test_session.commit()
        await test_session.refresh(user)
        assert user.id is not None  # ← ДОБАВИТЬ (используем переменную)

        authenticated = await repo.authenticate("auth_user", "wrong_password")
        assert authenticated is None

    async def test_authenticate_nonexistent_user(self, test_session):
        """Аутентификация несуществующего пользователя"""
        repo = UserRepository(test_session)
        authenticated = await repo.authenticate("nonexistent", "password")
        assert authenticated is None

    async def test_update_telegram_id(self, test_session):
        """Обновление telegram_id"""
        repo = UserRepository(test_session)
        user = await repo.create(
            username="telegram_user", password="pass123", role="instructor"
        )
        await test_session.commit()
        await test_session.refresh(user)

        updated = await repo.update_telegram_id(user.id, 123456789)
        await test_session.commit()
        await test_session.refresh(updated)

        assert updated is not None
        assert updated.telegram_id == 123456789

    async def test_get_all(self, test_session):
        """Получение всех пользователей"""
        repo = UserRepository(test_session)

        for i in range(3):
            await repo.create(
                username=f"user_{i}", password="pass123", role="instructor"
            )
        await test_session.commit()

        users = await repo.get_all()
        assert len(users) >= 3
