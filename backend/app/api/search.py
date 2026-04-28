from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateRead, SearchCreate
from app.services.sourcing import CandidateSourceResult, get_sourcing_connector

router = APIRouter(prefix="/api/search", tags=["search"])


def candidate_payload(result: CandidateSourceResult) -> dict[str, Any]:
    return {
        "linkedin_url": result.linkedin_url,
        "name": result.name,
        "headline": result.headline,
        "location": result.location,
        "current_company": result.current_company,
        "current_title": result.current_title,
    }


def upsert_candidate(session: Session, result: CandidateSourceResult) -> Candidate:
    candidate = session.exec(
        select(Candidate).where(Candidate.linkedin_url == result.linkedin_url)
    ).first()
    profile_data = {
        **candidate_payload(result),
        "raw": result.raw,
    }
    if candidate is None:
        candidate = Candidate(
            linkedin_url=result.linkedin_url,
            name=result.name,
            headline=result.headline,
            location=result.location,
            current_company=result.current_company,
            profile_data=profile_data,
        )
        session.add(candidate)
    else:
        candidate.name = result.name
        candidate.headline = result.headline
        candidate.location = result.location
        candidate.current_company = result.current_company
        candidate.profile_data = profile_data
        candidate.updated_at = datetime.now(UTC)
        session.add(candidate)
    session.flush()
    return candidate


@router.post("")
def create_search(
    search_create: SearchCreate, session: Session = Depends(get_session)
) -> dict[str, Any]:
    job = session.get(Job, search_create.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    search_run = SearchRun(
        job_id=search_create.job_id,
        query=search_create.query,
        provider=search_create.provider,
        status="running",
        run_metadata={"params": search_create.params},
    )
    session.add(search_run)
    session.commit()
    session.refresh(search_run)

    try:
        results = get_sourcing_connector().search_people(
            search_create.query, search_create.params
        )
    except Exception as exc:
        search_run.status = "failed"
        search_run.completed_at = datetime.now(UTC)
        search_run.run_metadata = {
            **search_run.run_metadata,
            "error_message": str(exc),
        }
        session.add(search_run)
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    candidates: list[Candidate] = []
    for rank, result in enumerate(results, start=1):
        candidate = upsert_candidate(session, result)
        candidates.append(candidate)
        session.add(
            SearchResult(
                search_run_id=search_run.id,
                candidate_id=candidate.id,
                linkedin_url=result.linkedin_url,
                title=result.current_title,
                snippet=result.headline,
                rank=rank,
                raw_data={
                    "normalized": candidate_payload(result),
                    "raw": result.raw,
                },
            )
        )

    search_run.status = "completed"
    search_run.completed_at = datetime.now(UTC)
    session.add(search_run)
    session.commit()

    for candidate in candidates:
        session.refresh(candidate)
    session.refresh(search_run)

    return {
        "id": search_run.id,
        "status": search_run.status,
        "candidates": [CandidateRead.model_validate(candidate) for candidate in candidates],
    }
