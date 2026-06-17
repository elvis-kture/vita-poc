from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./ticket_booking.db"
    hold_minutes: int = 15
    expiration_worker_interval_seconds: int = 60
    enable_expiration_worker: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TICKET_API_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
