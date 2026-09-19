from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/.env
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    monday_api_token: str
    monday_deals_board_id: int
    monday_work_orders_board_id: int

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()