from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bulk Certificate Generator"
    app_version: str = "1.0.0"

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/certificates"
    )

    redis_url: str = "redis://localhost:6379/0"

    storage_dir: str = "./storage/certificates"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
