from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables prefixed with ``ITEM_API_``."""

    model_config = SettingsConfigDict(env_prefix="ITEM_API_", env_file=".env", extra="ignore")

    app_name: str = "Item API"
    api_prefix: str = "/api"  # version segments come from api/v<N>/ routers
    debug: bool = False
    database_url: str = "sqlite:///./item_api.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
