from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.jobs import router as jobs_router
from app.api.reviews import router as reviews_router
from app.api.search import router as search_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if getattr(app.state, "create_tables_on_startup", True):
        init_db()
    yield


app = FastAPI(title="Talent Sourcing Tool", lifespan=lifespan)
app.state.create_tables_on_startup = True
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(reviews_router)
app.include_router(search_router)
