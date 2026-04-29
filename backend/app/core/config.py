from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_ROOT / 'talent_sourcing.sqlite3'}"
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    database_url: str = Field(
        default=DEFAULT_DATABASE_URL,
        validation_alias=AliasChoices("TALENT_DATABASE_URL", "DATABASE_URL"),
    )
    codex_binary: str = Field(
        default="codex",
        validation_alias=AliasChoices("TALENT_CODEX_BINARY", "CODEX_BINARY"),
    )
    review_workspace_root: str = Field(
        default=".codex-review-runs",
        validation_alias=AliasChoices("TALENT_REVIEW_WORKSPACE_ROOT", "REVIEW_WORKSPACE_ROOT"),
    )
    sourcing_provider: Literal["live", "brightdata"] = Field(
        default="live",
        validation_alias=AliasChoices("TALENT_SOURCING_PROVIDER", "SOURCING_PROVIDER"),
    )
    exa_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TALENT_EXA_API_KEY", "EXA_API_KEY"),
    )
    brightdata_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TALENT_BRIGHTDATA_API_KEY", "BRIGHTDATA_API_KEY"),
    )
    brightdata_zone: str = Field(
        default="",
        validation_alias=AliasChoices("TALENT_BRIGHTDATA_ZONE", "BRIGHTDATA_ZONE"),
    )

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", REPO_ROOT / ".env"),
        extra="ignore",
    )


settings = Settings()
