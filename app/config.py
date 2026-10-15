from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    db_host: str = "db"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "hireos"
    db_user: str = "hireos_app"
    db_password: SecretStr = Field(
        min_length=20, validation_alias=AliasChoices("DB_PASSWORD", "APP_DB_PASSWORD")
    )
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_issuer: str = "hireos-demo"
    jwt_audience: str = "hireos-api"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
