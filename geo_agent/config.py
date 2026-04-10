from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ANTHROPIC_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    OPENAI_API_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    MODEL_HEAVY: str = "claude-sonnet-4-20250514"
    MODEL_LIGHT: str = "claude-haiku-4-5-20251001"
    MAX_IMAGE_SIZE: int = 2048
    THINKING_BUDGET: int = 10000
    PIPELINE_TIMEOUT: int = 300
    RATE_LIMIT_PER_HOUR: int = 10


settings = Settings()
