"""Application settings, read from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql+psycopg://cairn:cairn@localhost:5432/cairn"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    sentry_dsn: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Git SHA of the deployed code; Render sets RENDER_GIT_COMMIT automatically.
    release: str = Field(
        default="", validation_alias=AliasChoices("RELEASE", "GIT_SHA", "RENDER_GIT_COMMIT")
    )

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Hosts such as Render give postgres:// URLs; SQLAlchemy needs the psycopg 3 driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
