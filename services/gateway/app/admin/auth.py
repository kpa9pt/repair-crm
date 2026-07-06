"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext

from shared import get_session_maker
from shared.models import User
from shared.auth import verify_password
from sqlalchemy import select


# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        # Ищем пользователя в БД
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False

            # Проверяем пароль
            if not verify_password(password, user.password_hash):
                return False

            # Проверяем роль (только admin и mechanic)
            if user.role not in ["admin", "mechanic"]:
                return False

            # ⚠️ ДОБАВЛЯЕМ: сохраняем user_id и username в сессию
            request.session.update(
                {
                    "admin_authenticated": True,
                    "user_id": user.id,  # ← ДОБАВИТЬ
                    "username": user.username,  # ← ДОБАВИТЬ
                }
            )
            return True

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)
