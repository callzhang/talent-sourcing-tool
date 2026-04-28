from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateRead, SearchCreate
from app.services.sourcing import CandidateSourceResult, get_sourcing_connector

router = APIRouter(prefix="/api/search", tags=["search"])


def json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [json_safe_value(item) for item in value]
    return str(value)


def canonical_linkedin_url(linkedin_url: str) -> str:
    parsed = urlsplit(linkedin_url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def candidate_payload(result: CandidateSourceResult) -> dict[str, Any]:
    return json_safe_value(
        {
            "linkedin_url": canonical_linkedin_url(result.linkedin_url),
            "name": result.name,
            "headline": result.headline,
            "location": result.location,
            "current_company": result.current_company,
            "current_title": result.current_title,
        }
    )


def normalize_result(result: CandidateSourceResult) -> CandidateSourceResult:
    return CandidateSourceResult(
        linkedin_url=canonical_linkedin_url(result.linkedin_url),
        name=result.name,
        headline=result.headline,
        location=result.location,
        current_company=result.current_company,
        current_title=result.current_title,
        raw=json_safe_value(result.raw),
    )


def dedupe_results(results: list[CandidateSourceResult]) -> list[CandidateSourceResult]:
    deduped: list[CandidateSourceResult] = []
    seen_urls: set[str] = set()
    for result in results:
        normalized = normalize_result(result)
        if normalized.linkedin_url in seen_urls:
            continue
        seen_urls.add(normalized.linkedin_url)
        deduped.append(normalized)
    return deduped


def mark_search_failed(session: Session, search_run_id: str, error_message: str) -> None:
    session.rollback()
    search_run = session.get(SearchRun, search_run_id)
    if search_run is None:
        return
    search_run.status = "failed"
    search_run.completed_at = datetime.now(UTC)
    search_run.run_metadata = {
        **search_run.run_metadata,
        "error_message": error_message,
    }
    session.add(search_run)
    session.commit()


def update_candidate(candidate: Candidate, result: CandidateSourceResult) -> Candidate:
    candidate.name = result.name
    candidate.headline = result.headline
    candidate.location = result.location
    candidate.current_company = result.current_company
    candidate.profile_data = {
        **candidate_payload(result),
        "raw": result.raw,
    }
    candidate.updated_at = datetime.now(UTC)
    return candidate


def upsert_candidate(session: Session, result: CandidateSourceResult) -> Candidate:
    candidate = session.exec(
        select(Candidate).where(Candidate.linkedin_url == result.linkedin_url)
    ).first()
    if candidate is None:
        candidate = Candidate(
            linkedin_url=result.linkedin_url,
            name=result.name,
            headline=result.headline,
            location=result.location,
            current_company=result.current_company,
            profile_data={
                **candidate_payload(result),
                "raw": result.raw,
            },
        )
        try:
            with session.begin_nested():
                session.add(candidate)
                session.flush()
        except IntegrityError:
            candidate = session.exec(
                select(Candidate).where(Candidate.linkedin_url == result.linkedin_url)
            ).one()
            update_candidate(candidate, result)
            session.add(candidate)
            session.flush()
    else:
        update_candidate(candidate, result)
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
        results = dedupe_results(
            get_sourcing_connector().search_people(search_create.query, search_create.params)
        )

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
    except Exception as exc:
        mark_search_failed(session, search_run.id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for candidate in candidates:
        session.refresh(candidate)
    session.refresh(search_run)

    return {
        "id": search_run.id,
        "status": search_run.status,
        "candidates": [CandidateRead.model_validate(candidate) for candidate in candidates],
    }
