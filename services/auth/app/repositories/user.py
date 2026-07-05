from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import User
from shared.auth import get_password_hash, verify_password
from typing import Optional


class UserRepository:
    """Репозиторий для работы с пользователями (только для Auth Service)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, username: str, password: str, role: str = "instructor"
    ) -> User:
        """Создать нового пользователя"""
        hashed_password = get_password_hash(password)
        user = User(username=username, password_hash=hashed_password, role=role)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = await self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def update_telegram_id(
        self, user_id: int, telegram_id: int
    ) -> Optional[User]:
        """Обновить telegram_id (для будущей интеграции)"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.telegram_id = telegram_id
        await self.session.flush()
        return user

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список всех пользователей (для админа)"""
        result = await self.session.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()
