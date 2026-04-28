from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./talent_sourcing.sqlite3"
    codex_binary: str = "codex"
    review_workspace_root: str = ".codex-review-runs"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TALENT_")


settings = Settings()
