import os
from datetime import datetime, timedelta, timezone  # ← добавить timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from .schemas import TokenData

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля через bcrypt"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Хеширование пароля через bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()

    # ✅ Конвертируем sub в строку (если он есть и это int)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")

        if user_id is None or username is None or role is None:
            raise JWTError("Missing required fields")

        # ✅ Конвертируем sub обратно в int
        return TokenData(
            sub=int(user_id), username=username, role=role  # ← обратно в int
        )

    except JWTError:
        raise JWTError("Invalid token")
