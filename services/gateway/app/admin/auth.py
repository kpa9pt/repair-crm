"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext
from shared.settings import get_settings

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()

        # Здесь можно заменить на чтение из БД или переменных окружения
        # Для старта - фиксированные учетные данные
        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)
