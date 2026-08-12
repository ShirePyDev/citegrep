"""Application configuration.

All runtime configuration comes from environment variables (or a local .env
file, which is never committed). Code reads settings through `get_settings()`
so tests can override values without touching the real environment.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "documind"
    log_level: str = "INFO"
    qdrant_url: str = "http://localhost:6333"


@lru_cache
def get_settings() -> Settings:
    """Build settings once per process; FastAPI injects this as a dependency."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
