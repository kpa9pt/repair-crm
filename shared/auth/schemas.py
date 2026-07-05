from pydantic import BaseModel, ConfigDict  # ← добавить импорт ConfigDict
from typing import Optional


class User(BaseModel):
    """Модель пользователя для авторизации (Pydantic)"""

    id: int
    username: str
    role: str
    telegram_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)  # ← заменить class Config


class Token(BaseModel):
    """Ответ с токеном"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Данные внутри JWT"""

    sub: int  # user_id
    username: str
    role: str


class UserCreate(BaseModel):
    """Создание пользователя"""

    username: str
    password: str
    role: str = "instructor"


class UserLogin(BaseModel):
    """Логин пользователя"""

    username: str
    password: str


class UserResponse(BaseModel):
    """Ответ с данными пользователя (без пароля)"""

    id: int
    username: str
    role: str
    telegram_id: Optional[int] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)  # ← заменить class Config
