from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_ROOT / 'talent_sourcing.sqlite3'}"


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    codex_binary: str = "codex"
    review_workspace_root: str = ".codex-review-runs"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TALENT_")


settings = Settings()
