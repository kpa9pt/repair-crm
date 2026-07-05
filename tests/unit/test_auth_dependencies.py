import pytest
from fastapi import HTTPException
from shared.auth import require_role, User


@pytest.mark.asyncio
class TestAuthDependencies:
    """Тесты зависимостей аутентификации"""

    async def test_require_role_allowed(self):
        """Проверка роли — разрешено"""
        dependency = require_role(["admin", "mechanic"])
        user = User(id=1, username="admin", role="admin")

        result = await dependency(user)
        assert result == user
        assert result.role == "admin"

    async def test_require_role_allowed_mechanic(self):
        """Проверка роли — механик разрешен"""
        dependency = require_role(["admin", "mechanic"])
        user = User(id=2, username="mechanic1", role="mechanic")

        result = await dependency(user)
        assert result == user
        assert result.role == "mechanic"

    async def test_require_role_forbidden(self):
        """Проверка роли — запрещено"""
        dependency = require_role(["admin", "mechanic"])
        user = User(id=3, username="instructor1", role="instructor")

        with pytest.raises(HTTPException) as exc:
            await dependency(user)

        assert exc.value.status_code == 403
        assert "Not enough permissions" in exc.value.detail

    async def test_require_role_single_allowed(self):
        """Проверка роли — только одна роль разрешена"""
        dependency = require_role(["admin"])
        user = User(id=1, username="admin", role="admin")

        result = await dependency(user)
        assert result == user

    async def test_require_role_single_forbidden(self):
        """Проверка роли — только одна роль, но у пользователя другая"""
        dependency = require_role(["admin"])
        user = User(id=3, username="instructor1", role="instructor")

        with pytest.raises(HTTPException) as exc:
            await dependency(user)

        assert exc.value.status_code == 403
