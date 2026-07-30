from __future__ import annotations

import os

from fastapi import HTTPException

from app.core.config import settings
from app.services.review_worker import resolve_review_provider


TMP_SQLITE_URL = "sqlite:////tmp/talent_sourcing.sqlite3"


def is_vercel_environment() -> bool:
    return os.environ.get("VERCEL") == "1"


def persistent_storage_configured() -> bool:
    return not (
        is_vercel_environment() and settings.database_url.strip() == TMP_SQLITE_URL
    )


def review_execution_configured() -> bool:
    review_provider = resolve_review_provider(settings)
    return review_provider != "openai" or bool(settings.openai_api_key.strip())


def require_persistent_storage_for_writes() -> None:
    if persistent_storage_configured():
        return
    raise HTTPException(
        status_code=503,
        detail=(
            "Production write actions are disabled until durable storage is configured. "
            "Set DATABASE_URL, TALENT_DATABASE_URL, or TURSO_DATABASE_URL with TURSO_AUTH_TOKEN."
        ),
    )


def require_review_execution_for_production() -> None:
    if review_execution_configured():
        return
    raise HTTPException(
        status_code=503,
        detail=(
            "Production AI review is disabled until TALENT_OPENAI_API_KEY is configured "
            "for the openai review provider."
        ),
    )
