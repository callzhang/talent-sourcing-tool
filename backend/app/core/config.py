import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def default_database_url() -> str:
    turso_database_url = os.environ.get("TURSO_DATABASE_URL")
    if turso_database_url:
        return turso_database_url
    if os.environ.get("VERCEL") == "1" and not os.environ.get("DATABASE_URL"):
        return "sqlite:////tmp/talent_sourcing.sqlite3"
    return f"sqlite:///{BACKEND_ROOT / 'talent_sourcing.sqlite3'}"


class Settings(BaseSettings):
    database_url: str = Field(
        default_factory=default_database_url,
        validation_alias=AliasChoices("TALENT_DATABASE_URL", "DATABASE_URL"),
    )
    turso_auth_token: str = Field(
        default="",
        validation_alias=AliasChoices("TALENT_TURSO_AUTH_TOKEN", "TURSO_AUTH_TOKEN"),
    )
    codex_binary: str = Field(
        default="codex",
        validation_alias=AliasChoices("TALENT_CODEX_BINARY", "CODEX_BINARY"),
    )
    review_workspace_root: str = Field(
        default=".codex-review-runs",
        validation_alias=AliasChoices("TALENT_REVIEW_WORKSPACE_ROOT", "REVIEW_WORKSPACE_ROOT"),
    )
    review_provider: Literal["auto", "codex", "openai"] = Field(
        default="auto",
        validation_alias=AliasChoices("TALENT_REVIEW_PROVIDER", "REVIEW_PROVIDER"),
    )
    review_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices("TALENT_REVIEW_MODEL", "REVIEW_MODEL"),
    )
    review_timeout_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices("TALENT_REVIEW_TIMEOUT_SECONDS", "REVIEW_TIMEOUT_SECONDS"),
    )
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TALENT_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("TALENT_OPENAI_BASE_URL", "OPENAI_BASE_URL"),
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
