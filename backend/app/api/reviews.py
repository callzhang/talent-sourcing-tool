from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import (
    Candidate,
    CandidateDecision,
    Job,
    PassReason,
    Review,
    ReviewJob,
    Rubric,
)
from app.db.session import get_session
from app.schemas import DecisionCreate, ReviewStart
from app.services.pass_reason import draft_pass_reason
from app.services.review_worker import ReviewWorker

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def latest_rubric_for_job(session: Session, job_id: str) -> Rubric | None:
    return session.exec(
        select(Rubric).where(Rubric.job_id == job_id).order_by(Rubric.created_at.desc())
    ).first()


def review_payload(job: Job, candidate: Candidate, rubric: Rubric) -> dict[str, Any]:
    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "target_profile_text": job.target_profile_text,
            "red_flags_text": job.red_flags_text,
            "search_notes": job.search_notes,
        },
        "candidate": {
            "id": candidate.id,
            "linkedin_url": candidate.linkedin_url,
            "name": candidate.name,
            "headline": candidate.headline,
            "location": candidate.location,
            "current_company": candidate.current_company,
            "profile_data": candidate.profile_data,
        },
        "rubric": {
            "id": rubric.id,
            "name": rubric.name,
            "criteria": rubric.criteria,
        },
    }


def mark_review_job_failed(session: Session, review_job_id: str, error_message: str) -> None:
    session.rollback()
    review_job = session.get(ReviewJob, review_job_id)
    if review_job is None:
        return
    review_job.status = "failed"
    review_job.error_message = error_message
    review_job.completed_at = datetime.now(UTC)
    session.add(review_job)
    session.commit()


@router.post("/start")
def start_review(
    review_start: ReviewStart, session: Session = Depends(get_session)
) -> dict[str, Any]:
    job = session.get(Job, review_start.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    candidate = session.get(Candidate, review_start.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    rubric = latest_rubric_for_job(session, job.id)
    if rubric is None:
        raise HTTPException(status_code=400, detail="Job has no rubric")

    review_job = ReviewJob(job_id=job.id, candidate_id=candidate.id, status="running")
    review_job.started_at = datetime.now(UTC)
    session.add(review_job)
    session.commit()
    session.refresh(review_job)

    worker = ReviewWorker(
        codex_command=[settings.codex_binary, "exec"],
        workspace_root=settings.review_workspace_root,
    )
    try:
        worker_result = worker.run_review(
            review_job.id,
            review_payload(job=job, candidate=candidate, rubric=rubric),
        )
    except Exception as exc:
        mark_review_job_failed(session, review_job.id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        review_data = worker_result.review
        review = Review(
            review_job_id=review_job.id,
            summary=str(review_data["decision_summary"]),
            evidence=review_data.get("evidence", []),
            recommendation=str(review_data["recommendation"]),
            score=float(review_data["overall_score"]),
            raw_review=review_data,
        )
        review_job.status = "completed"
        review_job.workspace_path = str(worker_result.workspace)
        review_job.input_path = str(worker_result.input_path)
        review_job.output_path = str(worker_result.output_path)
        review_job.completed_at = datetime.now(UTC)
        session.add(review_job)
        session.add(review)
        session.commit()
        session.refresh(review_job)
        session.refresh(review)
    except Exception as exc:
        mark_review_job_failed(session, review_job.id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "review_job_id": review_job.id,
        "review_id": review.id,
        "review": review_data,
    }


@router.get("/{review_id}/draft-pass-reason")
def get_draft_pass_reason(review_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    review = session.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    return draft_pass_reason(review.raw_review)


@router.post("/decision")
def create_decision(
    decision_create: DecisionCreate, session: Session = Depends(get_session)
) -> dict[str, Any]:
    job = session.get(Job, decision_create.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    candidate = session.get(Candidate, decision_create.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if decision_create.review_id is not None and session.get(Review, decision_create.review_id) is None:
        raise HTTPException(status_code=404, detail="Review not found")

    decision = CandidateDecision(
        job_id=decision_create.job_id,
        candidate_id=decision_create.candidate_id,
        review_id=decision_create.review_id,
        decision=decision_create.decision,
        notes=decision_create.notes,
        decided_by=decision_create.decided_by,
    )
    session.add(decision)
    session.flush()
    if decision_create.decision == "pass":
        session.add(
            PassReason(
                candidate_decision_id=decision.id,
                reason_code=decision_create.pass_reason_code,
                reason_text=decision_create.pass_reason_text or "",
                agent_suggested=False,
                user_edited=True,
            )
        )
    session.commit()

    session.refresh(decision)
    return {
        "id": decision.id,
        "job_id": decision.job_id,
        "candidate_id": decision.candidate_id,
        "review_id": decision.review_id,
        "decision": decision.decision,
        "notes": decision.notes,
        "decided_by": decision.decided_by,
    }
