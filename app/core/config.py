from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bulk Certificate Generator"
    app_version: str = "1.0.0"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/certificates",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL", "database_url", "db_url"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    storage_dir: str = Field(
        default="storage/certificates",
        validation_alias=AliasChoices("STORAGE_DIR", "storage_dir"),
    )

    @property
    def DB_URL(self) -> str:
        return self.database_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis_url

    @property
    def STORAGE_DIR(self) -> str:
        return self.storage_dir

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
