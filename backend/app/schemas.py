from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    title: str
    description: str
    target_profile_text: str = ""
    red_flags_text: str = ""
    search_notes: str = ""


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    target_profile_text: str
    red_flags_text: str
    search_notes: str
    status: str
    created_at: datetime
    updated_at: datetime


class RubricRead(BaseModel):
    id: str
    job_id: str
    version: int
    source_hash: str
    rubric: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobWithRubric(BaseModel):
    job: JobRead
    rubric: RubricRead


class SearchCreate(BaseModel):
    job_id: str
    query: str
    provider: str = "bright_data"


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    linkedin_url: str
    name: str
    headline: str | None = None
    location: str | None = None
    current_company: str | None = None
    profile_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReviewStart(BaseModel):
    job_id: str
    candidate_id: str


class DecisionCreate(BaseModel):
    job_id: str
    candidate_id: str
    review_id: str | None = None
    decision: str
    notes: str | None = None
    decided_by: str = "agent"
