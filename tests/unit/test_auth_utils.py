import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from shared.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
)
from shared.auth.utils import SECRET_KEY  # ← ИМПОРТИРУЕМ КОНСТАНТУ


class TestAuthUtils:
    """Тесты утилит аутентификации"""

    def test_password_hashing(self):
        """Хеширование и проверка пароля"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        # Хеш не равен исходному паролю
        assert hashed != password

        # Проверка правильного пароля
        assert verify_password(password, hashed)

        # Проверка неправильного пароля
        assert not verify_password("wrong_password", hashed)

        # Разные пароли дают разные хеши
        another_hash = get_password_hash("another_password")
        assert hashed != another_hash

    def test_create_access_token(self):
        """Создание JWT токена"""
        data = {"sub": 1, "username": "testuser", "role": "admin"}
        token = create_access_token(data)

        # Токен должен быть строкой
        assert isinstance(token, str)
        assert len(token) > 0

        # Декодируем и проверяем
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])  # ← изменено
        assert decoded["sub"] == "1"  # JWT хранит как строку
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_create_access_token_with_expiry(self):
        """Создание токена с кастомным временем жизни"""
        data = {"sub": 1, "username": "testuser", "role": "admin"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])  # ← изменено

        # Проверяем что exp примерно через 30 минут
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp_time - now

        # Допускаем погрешность в пару секунд
        assert 29 * 60 <= diff.total_seconds() <= 31 * 60

    def test_decode_token_valid(self):
        """Декодирование валидного токена"""
        token = create_access_token(
            {"sub": 42, "username": "valid_user", "role": "instructor"}
        )

        token_data = decode_token(token)
        assert token_data.sub == 42
        assert token_data.username == "valid_user"
        assert token_data.role == "instructor"

    def test_decode_token_invalid(self):
        """Декодирование невалидного токена"""
        with pytest.raises(Exception):
            decode_token("invalid.token.here")

        with pytest.raises(Exception):
            decode_token("")

        with pytest.raises(Exception):
            decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid")

    def test_decode_token_missing_fields(self):
        """Декодирование токена с пропущенными полями"""
        # Токен без username
        token = create_access_token({"sub": 1, "role": "admin"})
        with pytest.raises(Exception):
            decode_token(token)

        # Токен без role
        token = create_access_token({"sub": 1, "username": "testuser"})
        with pytest.raises(Exception):
            decode_token(token)
