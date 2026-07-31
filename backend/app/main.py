from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.candidates import router as candidates_router
from app.api.jobs import router as jobs_router
from app.api.reviews import router as reviews_router
from app.api.search import router as search_router
from app.api.system import router as system_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if should_initialize_schema(app):
        init_db()
    yield


def should_initialize_schema(app: FastAPI) -> bool:
    """Keep local startup convenient without mutating the remote DB per Vercel instance."""
    return (
        getattr(app.state, "create_tables_on_startup", True)
        and os.environ.get("VERCEL") != "1"
    )


def register_api_routers(app: FastAPI, *, prefixes: list[str]) -> None:
    for prefix in prefixes:
        normalized_prefix = prefix.rstrip("/")
        if normalized_prefix == "/":
            normalized_prefix = ""
        app.include_router(candidates_router, prefix=normalized_prefix)
        app.include_router(jobs_router, prefix=normalized_prefix)
        app.include_router(reviews_router, prefix=normalized_prefix)
        app.include_router(search_router, prefix=normalized_prefix)
        app.include_router(system_router, prefix=normalized_prefix)


def create_app(*, api_prefix: str = "/api") -> FastAPI:
    app = FastAPI(title="Talent Sourcing Tool", lifespan=lifespan)
    app.state.create_tables_on_startup = True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_api_routers(app, prefixes=[api_prefix])
    return app


app = create_app()
