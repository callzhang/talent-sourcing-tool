from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(UTC)


def prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def job_id() -> str:
    return prefixed_id("job")


def rubric_id() -> str:
    return prefixed_id("rubric")


def search_run_id() -> str:
    return prefixed_id("search_run")


def candidate_id() -> str:
    return prefixed_id("candidate")


def search_result_id() -> str:
    return prefixed_id("search_result")


def candidate_source_id() -> str:
    return prefixed_id("candidate_source")


def review_job_id() -> str:
    return prefixed_id("review_job")


def review_id() -> str:
    return prefixed_id("review")


def candidate_decision_id() -> str:
    return prefixed_id("decision")


def pass_reason_id() -> str:
    return prefixed_id("pass_reason")


def user_feedback_id() -> str:
    return prefixed_id("feedback")


def refinement_suggestion_id() -> str:
    return prefixed_id("refinement")


class Job(SQLModel, table=True):
    id: str = Field(default_factory=job_id, primary_key=True)
    title: str
    description: str
    target_profile_text: str = ""
    red_flags_text: str = ""
    search_notes: str = ""
    status: str = Field(default="draft", index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Rubric(SQLModel, table=True):
    id: str = Field(default_factory=rubric_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    name: str
    criteria: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SearchRun(SQLModel, table=True):
    id: str = Field(default_factory=search_run_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    query: str
    provider: str = Field(default="bright_data")
    status: str = Field(default="pending", index=True)
    run_metadata: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=now_utc)
    completed_at: datetime | None = None


class Candidate(SQLModel, table=True):
    id: str = Field(default_factory=candidate_id, primary_key=True)
    linkedin_url: str = Field(unique=True, index=True)
    name: str
    headline: str | None = None
    location: str | None = None
    current_company: str | None = None
    profile_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SearchResult(SQLModel, table=True):
    id: str = Field(default_factory=search_result_id, primary_key=True)
    search_run_id: str = Field(foreign_key="searchrun.id", index=True)
    candidate_id: str | None = Field(default=None, foreign_key="candidate.id", index=True)
    linkedin_url: str = Field(index=True)
    title: str | None = None
    snippet: str | None = None
    rank: int | None = None
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class CandidateSource(SQLModel, table=True):
    id: str = Field(default_factory=candidate_source_id, primary_key=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    source_type: str
    source_url: str
    title: str | None = None
    content: str | None = None
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class ReviewJob(SQLModel, table=True):
    id: str = Field(default_factory=review_job_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    status: str = Field(default="pending", index=True)
    workspace_path: str | None = None
    input_path: str | None = None
    output_path: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Review(SQLModel, table=True):
    id: str = Field(default_factory=review_id, primary_key=True)
    review_job_id: str = Field(foreign_key="reviewjob.id", index=True)
    summary: str
    evidence: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    recommendation: str = Field(index=True)
    score: float | None = None
    raw_review: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class CandidateDecision(SQLModel, table=True):
    id: str = Field(default_factory=candidate_decision_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    review_id: str | None = Field(default=None, foreign_key="review.id", index=True)
    decision: str = Field(index=True)
    notes: str | None = None
    decided_by: str = Field(default="agent")
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class PassReason(SQLModel, table=True):
    id: str = Field(default_factory=pass_reason_id, primary_key=True)
    candidate_decision_id: str = Field(foreign_key="candidatedecision.id", index=True)
    reason_code: str = Field(index=True)
    reason_text: str
    agent_suggested: bool = Field(default=True)
    user_edited: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now_utc)


class UserFeedback(SQLModel, table=True):
    id: str = Field(default_factory=user_feedback_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    candidate_id: str | None = Field(default=None, foreign_key="candidate.id", index=True)
    candidate_decision_id: str | None = Field(
        default=None, foreign_key="candidatedecision.id", index=True
    )
    feedback_type: str = Field(index=True)
    feedback_text: str
    feedback_metadata: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=now_utc)


class RefinementSuggestion(SQLModel, table=True):
    id: str = Field(default_factory=refinement_suggestion_id, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    pass_reason_id: str | None = Field(default=None, foreign_key="passreason.id", index=True)
    suggestion_type: str = Field(index=True)
    suggestion_text: str
    status: str = Field(default="pending", index=True)
    suggestion_metadata: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=now_utc)
    applied_at: datetime | None = None
