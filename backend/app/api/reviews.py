from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.deployment_guard import (
    require_persistent_storage_for_writes,
    require_review_execution_for_production,
)
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
from app.schemas import DecisionCreate, ReviewJobRead, ReviewRead, ReviewStart, ReviewStartResult
from app.services.pass_reason import draft_pass_reason, suggest_refinements
from app.services.review_worker import ReviewRunner, build_review_runner, validate_review_output

router = APIRouter(prefix="/reviews", tags=["reviews"])


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
            "profile_url": candidate.profile_url,
            "profile_source": candidate.profile_source,
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
    normalized_review = normalize_review_data(review.raw_review)
    return ReviewRead(
        id=review.id,
        review_job_id=review.review_job_id,
        job_id=review_job.job_id,
        candidate_id=review_job.candidate_id,
        summary=review.summary,
        evidence=normalize_review_evidence(review.evidence),
        recommendation=review.recommendation,
        score=review.score,
        review=normalized_review,
        created_at=review.created_at,
    )


def read_review_job(session: Session, review_job: ReviewJob) -> ReviewJobRead:
    review = session.exec(
        select(Review)
        .where(Review.review_job_id == review_job.id)
        .order_by(Review.created_at.desc())
    ).first()
    review_id = review.id if review else None
    normalized_review = normalize_review_data(review.raw_review) if review else None
    return ReviewJobRead(
        id=review_job.id,
        job_id=review_job.job_id,
        candidate_id=review_job.candidate_id,
        status=review_job.status,
        error_message=review_job.error_message,
        created_at=review_job.created_at,
        started_at=review_job.started_at,
        completed_at=review_job.completed_at,
        review_id=review_id,
        review=normalized_review,
    )


def _claim_pending_review_job(session: Session, review_job_id: str) -> ReviewJob | None:
    review_job = session.get(ReviewJob, review_job_id)
    if review_job is None or review_job.status != "pending":
        return review_job
    review_job.status = "running"
    review_job.started_at = datetime.now(UTC)
    session.add(review_job)
    session.commit()
    session.refresh(review_job)
    return review_job


def process_review_job(
    session: Session,
    review_job_id: str,
    *,
    worker: ReviewRunner | None = None,
) -> ReviewJob:
    review_job = _claim_pending_review_job(session, review_job_id)
    if review_job is None:
        raise HTTPException(status_code=404, detail="Review job not found")
    if review_job.status != "running":
        return review_job

    job = session.get(Job, review_job.job_id)
    if job is None:
        mark_review_job_failed(session, review_job.id, "Job not found")
        return session.get(ReviewJob, review_job.id)  # type: ignore[return-value]
    candidate = session.get(Candidate, review_job.candidate_id)
    if candidate is None:
        mark_review_job_failed(session, review_job.id, "Candidate not found")
        return session.get(ReviewJob, review_job.id)  # type: ignore[return-value]
    rubric = latest_rubric_for_job(session, job.id)
    if rubric is None:
        mark_review_job_failed(session, review_job.id, "Job has no rubric")
        return session.get(ReviewJob, review_job.id)  # type: ignore[return-value]

    try:
        runner = worker or build_review_runner(settings)
        worker_result = runner.run_review(
            review_job.id,
            review_payload(job=job, candidate=candidate, rubric=rubric),
        )
    except Exception as exc:
        mark_review_job_failed(session, review_job.id, str(exc))
        return session.get(ReviewJob, review_job.id)  # type: ignore[return-value]

    try:
        # Runners are pluggable, so validate here as well as inside the concrete workers.
        # Only legacy records may use display normalization without satisfying the new contract.
        review_data = normalize_review_data(
            validate_review_output(worker_result.review).model_dump(mode="json")
        )
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
        review_job.workspace_path = str(worker_result.workspace) if worker_result.workspace else None
        review_job.input_path = str(worker_result.input_path) if worker_result.input_path else None
        review_job.output_path = str(worker_result.output_path) if worker_result.output_path else None
        review_job.completed_at = datetime.now(UTC)
        session.add(review_job)
        session.add(review)
        session.commit()
    except Exception as exc:
        mark_review_job_failed(session, review_job.id, str(exc))

    refreshed_review_job = session.get(ReviewJob, review_job.id)
    if refreshed_review_job is None:
        raise HTTPException(status_code=404, detail="Review job not found")
    return refreshed_review_job


def normalize_review_evidence(evidence: Any) -> list[dict[str, Any]]:
    if not isinstance(evidence, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(evidence, start=1):
        if isinstance(item, dict):
            normalized_item = dict(item)
            claim = _review_evidence_text(normalized_item.get("claim"))
            label = _review_evidence_text(normalized_item.get("label")) or claim
            detail = _review_evidence_detail(normalized_item)
            normalized_item["label"] = label or f"证据 {index}"
            normalized_item["claim"] = claim or normalized_item["label"]
            normalized_item["detail"] = detail or "历史评审未保留证据详情，不能作为决策依据。"
            source_url = _review_evidence_text(
                normalized_item.get("source_url") or normalized_item.get("url")
            )
            if source_url:
                normalized_item["source_url"] = source_url
            normalized.append(normalized_item)
            continue
        detail = str(item).strip()
        normalized.append(
            {
                "label": f"证据 {index}",
                "claim": detail or f"证据 {index}",
                "detail": detail or "历史评审未保留证据详情，不能作为决策依据。",
                "source_url": None,
            }
        )
    return normalized


def _review_evidence_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _review_evidence_detail(item: dict[str, Any]) -> str | None:
    for field in ("detail", "quote", "summary", "rationale", "evidence", "reason", "content"):
        detail = _review_evidence_text(item.get(field))
        if detail:
            return detail
    return None


def normalize_review_data(review_data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(review_data)
    normalized["evidence"] = normalize_review_evidence(review_data.get("evidence", []))
    return normalized


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


@router.get("/latest-job", response_model=ReviewJobRead | None)
def get_latest_review_job(
    job_id: str,
    candidate_id: str,
    session: Session = Depends(get_session),
) -> ReviewJobRead | None:
    if session.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if session.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    review_job = session.exec(
        select(ReviewJob)
        .where(ReviewJob.job_id == job_id, ReviewJob.candidate_id == candidate_id)
        .order_by(ReviewJob.created_at.desc())
    ).first()
    if review_job is None:
        return None
    return read_review_job(session, review_job)


@router.get("/jobs/{review_job_id}", response_model=ReviewJobRead)
def get_review_job(review_job_id: str, session: Session = Depends(get_session)) -> ReviewJobRead:
    review_job = session.get(ReviewJob, review_job_id)
    if review_job is None:
        raise HTTPException(status_code=404, detail="Review job not found")
    return read_review_job(session, review_job)


@router.post("/jobs/{review_job_id}/run", response_model=ReviewJobRead)
def run_review_job(review_job_id: str, session: Session = Depends(get_session)) -> ReviewJobRead:
    review_job = process_review_job(session, review_job_id)
    return read_review_job(session, review_job)


@router.post("/start", response_model=ReviewStartResult)
def start_review(
    review_start: ReviewStart, session: Session = Depends(get_session)
) -> ReviewStartResult:
    require_persistent_storage_for_writes()
    require_review_execution_for_production()
    job = session.get(Job, review_start.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    candidate = session.get(Candidate, review_start.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    rubric = latest_rubric_for_job(session, job.id)
    if rubric is None:
        raise HTTPException(status_code=400, detail="Job has no rubric")

    review_job = ReviewJob(job_id=job.id, candidate_id=candidate.id, status="pending")
    session.add(review_job)
    session.commit()
    session.refresh(review_job)

    return ReviewStartResult(
        review_job_id=review_job.id,
        status=review_job.status,
        review_id=None,
        review=None,
    )


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
    require_persistent_storage_for_writes()
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
