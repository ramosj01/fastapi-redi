import os
import socket
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Twelve-factor configuration: every instance is configured from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "fastapi-redi"
    environment: str = "local"
    log_level: str = "INFO"
    # Identifies this replica in logs/response headers; defaults to the container hostname.
    instance_id: str = Field(default_factory=lambda: os.getenv("HOSTNAME", socket.gethostname()))

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    cache_key_prefix: str = "fastapi-redi"
    cache_default_ttl_seconds: int = 300
    cache_lock_timeout_seconds: float = 5.0
    cache_lock_wait_seconds: float = 2.0

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
