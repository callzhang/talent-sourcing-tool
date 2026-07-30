from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.deployment_guard import require_persistent_storage_for_writes
from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateRead, SearchCreate, SearchRunDetail, SearchRunRead
from app.services.sourcing import (
    CandidateSourceResult,
    SourcingConfigError,
    canonical_profile_url,
    default_job_search_channels,
    get_sourcing_connector,
    normalize_search_channels,
)

router = APIRouter(prefix="/search", tags=["search"])


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


def candidate_payload(result: CandidateSourceResult) -> dict[str, Any]:
    return json_safe_value(
        {
            "profile_url": canonical_profile_url(result.profile_url),
            "profile_source": result.profile_source,
            "name": result.name,
            "headline": result.headline,
            "location": result.location,
            "current_company": result.current_company,
            "current_title": result.current_title,
        }
    )


def normalize_result(result: CandidateSourceResult) -> CandidateSourceResult:
    return CandidateSourceResult(
        profile_url=canonical_profile_url(result.profile_url),
        profile_source=result.profile_source,
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
        if normalized.profile_url in seen_urls:
            continue
        seen_urls.add(normalized.profile_url)
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
    candidate.profile_source = result.profile_source
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
        select(Candidate).where(Candidate.profile_url == result.profile_url)
    ).first()
    if candidate is None:
        candidate = Candidate(
            profile_url=result.profile_url,
            profile_source=result.profile_source,
            name=result.name,
            headline=result.headline,
            location=result.location,
            current_company=result.current_company,
            profile_data={
                **candidate_payload(result),
                "raw": result.raw,
            },
        )
        session.add(candidate)
        try:
            session.flush()
        except IntegrityError:
            # libSQL remote connections do not implement SQLite savepoints. Each
            # prior search result is committed before the next candidate is flushed,
            # so a uniqueness race can safely roll back only the current candidate.
            session.rollback()
            candidate = session.exec(
                select(Candidate).where(Candidate.profile_url == result.profile_url)
            ).one()
            update_candidate(candidate, result)
            session.add(candidate)
            session.flush()
    else:
        update_candidate(candidate, result)
        session.add(candidate)
        session.flush()
    return candidate


def search_run_params(search_run: SearchRun) -> dict[str, Any]:
    params = search_run.run_metadata.get("params", {})
    return params if isinstance(params, dict) else {}


def search_run_channels(search_run: SearchRun) -> list[str]:
    channels = search_run.run_metadata.get("channels", [])
    return normalize_search_channels(channels)


def candidate_count_for_run(session: Session, search_run_id: str) -> int:
    return len(
        session.exec(
            select(SearchResult.id).where(SearchResult.search_run_id == search_run_id)
        ).all()
    )


def read_search_run(session: Session, search_run: SearchRun) -> SearchRunRead:
    return SearchRunRead(
        id=search_run.id,
        job_id=search_run.job_id,
        query=search_run.query,
        provider=search_run.provider,
        channels=search_run_channels(search_run),
        status=search_run.status,
        params=search_run_params(search_run),
        candidate_count=candidate_count_for_run(session, search_run.id),
        created_at=search_run.created_at,
        completed_at=search_run.completed_at,
    )


@router.get("", response_model=list[SearchRunRead])
def list_search_runs(
    job_id: str | None = None, session: Session = Depends(get_session)
) -> list[SearchRunRead]:
    statement = select(SearchRun).order_by(SearchRun.created_at.desc())
    if job_id is not None:
        statement = statement.where(SearchRun.job_id == job_id)
    search_runs = session.exec(statement).all()
    return [read_search_run(session, search_run) for search_run in search_runs]


@router.get("/{search_run_id}", response_model=SearchRunDetail)
def get_search_run(
    search_run_id: str, session: Session = Depends(get_session)
) -> SearchRunDetail:
    search_run = session.get(SearchRun, search_run_id)
    if search_run is None:
        raise HTTPException(status_code=404, detail="Search run not found")

    search_results = session.exec(
        select(SearchResult)
        .where(SearchResult.search_run_id == search_run.id)
        .order_by(SearchResult.rank.asc())
    ).all()
    candidates = [
        candidate
        for candidate in (
            session.get(Candidate, search_result.candidate_id)
            for search_result in search_results
            if search_result.candidate_id is not None
        )
        if candidate is not None
    ]
    return SearchRunDetail(
        **read_search_run(session, search_run).model_dump(),
        candidates=[CandidateRead.model_validate(candidate) for candidate in candidates],
    )


@router.post("")
def create_search(
    search_create: SearchCreate, session: Session = Depends(get_session)
) -> dict[str, Any]:
    require_persistent_storage_for_writes()
    job = session.get(Job, search_create.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    search_run = SearchRun(
        job_id=search_create.job_id,
        query=search_create.query,
        provider=search_create.provider,
        status="running",
        run_metadata={
            "params": {
                **search_create.params,
                "region": job.region.strip(),
            },
            "channels": normalize_search_channels(search_create.channels)
            or job.search_channels
            or default_job_search_channels(job.title, job.description),
        },
    )
    session.add(search_run)
    session.commit()
    session.refresh(search_run)

    try:
        results = dedupe_results(
            get_sourcing_connector().search_people(
                search_create.query,
                {
                    **search_run_params(search_run),
                    "channels": search_run_channels(search_run),
                },
            )
        )

        candidates: list[Candidate] = []
        for rank, result in enumerate(results, start=1):
            candidate = upsert_candidate(session, result)
            candidates.append(candidate)
            session.add(
                SearchResult(
                    search_run_id=search_run.id,
                    candidate_id=candidate.id,
                    profile_url=result.profile_url,
                    title=result.current_title,
                    snippet=result.headline,
                    rank=rank,
                    raw_data={
                        "normalized": candidate_payload(result),
                        "raw": result.raw,
                    },
                )
            )
            session.commit()

        search_run.status = "completed"
        search_run.completed_at = datetime.now(UTC)
        session.add(search_run)
        session.commit()
    except (SourcingConfigError, Exception) as exc:
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
