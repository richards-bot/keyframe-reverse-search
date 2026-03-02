from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Keyframe Reverse Search"
    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    # Security
    api_key: str | None = Field(default=None, description="If set, require X-API-Key for mutation/export endpoints")
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    max_upload_mb: int = 300

    # Queue
    queue_workers: int = 2


settings = Settings()
