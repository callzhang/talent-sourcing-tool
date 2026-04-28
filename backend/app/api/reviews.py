from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.core.config import settings
from app.db.models import (
    Candidate,
    CandidateDecision,
    Job,
    PassReason,
    RefinementSuggestion,
    Review,
    ReviewJob,
    Rubric,
)
from app.db.session import get_session
from app.schemas import DecisionCreate, ReviewRead, ReviewStart
from app.services.pass_reason import draft_pass_reason, suggest_refinements
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
            "region": job.region,
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


def pass_reasons_for_job(session: Session, job_id: str) -> list[dict[str, Any]]:
    decisions = session.exec(
        select(CandidateDecision.id).where(CandidateDecision.job_id == job_id)
    ).all()
    if not decisions:
        return []

    pass_reasons = session.exec(
        select(PassReason).where(col(PassReason.candidate_decision_id).in_(decisions))
    ).all()
    return [
        {
            "id": pass_reason.id,
            "reason_code": pass_reason.reason_code,
            "reason_text": pass_reason.reason_text,
        }
        for pass_reason in pass_reasons
    ]


def persist_refinement_suggestions(
    session: Session,
    job_id: str,
    pass_reason: PassReason,
) -> None:
    existing_signatures = {
        _suggestion_signature(
            suggestion.suggestion_type,
            suggestion.suggestion_text,
            suggestion.suggestion_metadata.get("reason_codes", []),
        )
        for suggestion in session.exec(
            select(RefinementSuggestion).where(
                RefinementSuggestion.job_id == job_id,
                RefinementSuggestion.status == "pending",
            )
        ).all()
    }

    for suggestion in suggest_refinements(pass_reasons_for_job(session, job_id)):
        reason_codes = _normalized_reason_codes(suggestion.get("reason_codes", []))
        suggestion_type = str(suggestion["suggestion_type"])
        suggestion_text = str(suggestion["suggestion_text"])
        signature = _suggestion_signature(suggestion_type, suggestion_text, reason_codes)
        if signature in existing_signatures:
            continue

        session.add(
            RefinementSuggestion(
                job_id=job_id,
                pass_reason_id=(
                    pass_reason.id if pass_reason.reason_code in set(reason_codes) else None
                ),
                suggestion_type=suggestion_type,
                suggestion_text=suggestion_text,
                suggestion_metadata={"reason_codes": list(reason_codes)},
            )
        )
        existing_signatures.add(signature)


def _normalized_reason_codes(reason_codes: Any) -> tuple[str, ...]:
    if not isinstance(reason_codes, list | tuple):
        return ()
    return tuple(sorted(str(reason_code) for reason_code in reason_codes if reason_code))


def _suggestion_signature(
    suggestion_type: str,
    suggestion_text: str,
    reason_codes: Any,
) -> tuple[str, str, tuple[str, ...]]:
    return (
        suggestion_type,
        suggestion_text,
        _normalized_reason_codes(reason_codes),
    )


def read_review(session: Session, review: Review) -> ReviewRead:
    review_job = session.get(ReviewJob, review.review_job_id)
    if review_job is None:
        raise HTTPException(status_code=404, detail="Review job not found")
    return ReviewRead(
        id=review.id,
        review_job_id=review.review_job_id,
        job_id=review_job.job_id,
        candidate_id=review_job.candidate_id,
        summary=review.summary,
        evidence=review.evidence,
        recommendation=review.recommendation,
        score=review.score,
        review=review.raw_review,
        created_at=review.created_at,
    )


def validate_review_identity(
    review_data: dict[str, Any],
    review_job: ReviewJob,
    job: Job,
    candidate: Candidate,
) -> None:
    if review_job.job_id != job.id or review_job.candidate_id != candidate.id:
        raise ValueError("Review job does not match current job and candidate")

    if review_data["job_id"] != job.id or review_data["candidate_id"] != candidate.id:
        raise ValueError(
            "Review output does not match review job: "
            f"expected job_id={job.id}, candidate_id={candidate.id}; "
            f"got job_id={review_data['job_id']}, candidate_id={review_data['candidate_id']}"
        )


@router.get("/latest", response_model=ReviewRead | None)
def get_latest_review(
    job_id: str,
    candidate_id: str,
    session: Session = Depends(get_session),
) -> ReviewRead | None:
    if session.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if session.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    review_jobs = session.exec(
        select(ReviewJob.id)
        .where(ReviewJob.job_id == job_id, ReviewJob.candidate_id == candidate_id)
        .order_by(ReviewJob.created_at.desc())
    ).all()
    if not review_jobs:
        return None

    review = session.exec(
        select(Review)
        .where(col(Review.review_job_id).in_(review_jobs))
        .order_by(Review.created_at.desc())
    ).first()
    if review is None:
        return None
    return read_review(session, review)


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
        validate_review_identity(
            review_data=review_data,
            review_job=review_job,
            job=job,
            candidate=candidate,
        )
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


@router.get("/refinements")
def list_refinement_suggestions(
    job_id: str, session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    if session.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    suggestions = session.exec(
        select(RefinementSuggestion)
        .where(RefinementSuggestion.job_id == job_id)
        .order_by(RefinementSuggestion.created_at.desc())
    ).all()
    return [
        {
            "id": suggestion.id,
            "job_id": suggestion.job_id,
            "pass_reason_id": suggestion.pass_reason_id,
            "suggestion_type": suggestion.suggestion_type,
            "suggestion_text": suggestion.suggestion_text,
            "status": suggestion.status,
            "suggestion_metadata": suggestion.suggestion_metadata,
            "created_at": suggestion.created_at,
            "applied_at": suggestion.applied_at,
        }
        for suggestion in suggestions
    ]


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
    if decision_create.review_id is not None:
        review = session.get(Review, decision_create.review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Review not found")
        review_job = session.get(ReviewJob, review.review_job_id)
        if review_job is None:
            raise HTTPException(status_code=404, detail="Review job not found")
        if (
            review_job.job_id != decision_create.job_id
            or review_job.candidate_id != decision_create.candidate_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Review does not belong to job and candidate",
            )

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
        pass_reason = PassReason(
            candidate_decision_id=decision.id,
            reason_code=decision_create.pass_reason_code,
            reason_text=decision_create.pass_reason_text or "",
            agent_suggested=False,
            user_edited=True,
        )
        session.add(pass_reason)
        session.flush()
        persist_refinement_suggestions(session, decision_create.job_id, pass_reason)
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
