from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
    )
    telegram_token: str | None = None
    secret_key: str | None = None  # Добавляем это поле
    admin_username: str = "admin"  # Добавляем с дефолтом
    admin_password: str = "admin123"  # Добавляем с дефолтом
    domain_name: str = "localhost"

    # ✅ ДОБАВЛЯЕМ
    telegram_chat_id: str | None = None
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
