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

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
