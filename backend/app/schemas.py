from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCreate(BaseModel):
    title: str
    description: str
    region: str = ""
    target_profile_text: str = ""
    red_flags_text: str = ""
    search_notes: str = ""
    search_channels: list[str] = Field(default_factory=list)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    region: str
    target_profile_text: str
    red_flags_text: str
    search_notes: str
    search_channels: list[str]
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
    channels: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_url: str
    profile_source: str
    name: str
    headline: str | None = None
    location: str | None = None
    current_company: str | None = None
    profile_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CandidateListItem(CandidateRead):
    last_search_run_id: str | None = None
    last_search_query: str | None = None
    last_search_rank: int | None = None


class SearchRunRead(BaseModel):
    id: str
    job_id: str
    query: str
    provider: str
    channels: list[str]
    status: str
    params: dict[str, Any]
    candidate_count: int
    created_at: datetime
    completed_at: datetime | None


class SearchRunDetail(SearchRunRead):
    candidates: list[CandidateRead]


class ReviewRead(BaseModel):
    id: str
    review_job_id: str
    job_id: str
    candidate_id: str
    summary: str
    evidence: list[dict[str, Any]]
    recommendation: str
    score: float | None
    review: dict[str, Any]
    created_at: datetime


class ReviewJobRead(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    status: str
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    review_id: str | None = None
    review: dict[str, Any] | None = None


class ReviewStart(BaseModel):
    job_id: str
    candidate_id: str


class ReviewStartResult(BaseModel):
    review_job_id: str
    status: str
    review_id: str | None = None
    review: dict[str, Any] | None = None


class DecisionCreate(BaseModel):
    job_id: str
    candidate_id: str
    review_id: str | None = None
    decision: str
    notes: str | None = None
    decided_by: str = "agent"
    pass_reason_code: str = "manual_pass"
    pass_reason_text: str | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> "DecisionCreate":
        if self.decision not in {"pass", "proceed"}:
            raise ValueError("decision must be pass or proceed")
        if self.pass_reason_text is not None:
            self.pass_reason_text = self.pass_reason_text.strip()
        if self.decision == "pass" and not self.pass_reason_text:
            raise ValueError("pass_reason_text is required for pass decisions")
        return self
