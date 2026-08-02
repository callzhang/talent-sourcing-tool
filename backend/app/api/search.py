from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from unicodedata import normalize as unicode_normalize
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.deployment_guard import require_persistent_storage_for_writes
from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateRead, SearchCreate, SearchRunDetail, SearchRunRead
from app.services.sourcing import (
    CandidateSourceResult,
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
        profile_url=normalized_candidate_url(result.profile_url),
        profile_source=result.profile_source,
        name=result.name,
        headline=result.headline,
        location=result.location,
        current_company=result.current_company,
        current_title=result.current_title,
        raw=json_safe_value(result.raw),
    )


def normalized_identity_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unicode_normalize("NFKC", value).casefold().split())


def normalized_candidate_url(profile_url: str) -> str:
    canonical_url = canonical_profile_url(profile_url)
    parsed = urlsplit(canonical_url)
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname.startswith("www."):
        hostname = hostname.removeprefix("www.")
    port = parsed.port
    netloc = hostname if port is None or port == 443 else f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    if hostname in {"linkedin.com", "github.com"}:
        path = path.casefold()
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunsplit(("https", netloc, path, query, ""))


def candidate_identity_keys(result: CandidateSourceResult) -> set[str]:
    keys = {f"url:{normalized_candidate_url(result.profile_url)}"}
    name = normalized_identity_text(result.name)
    company = normalized_identity_text(result.current_company)
    location = normalized_identity_text(result.location)
    title = normalized_identity_text(result.current_title)
    if name and company:
        keys.add(f"identity:{name}|company:{company}")
    elif name and location and title:
        keys.add(f"identity:{name}|location:{location}|title:{title}")
    return keys


def dedupe_results(results: list[CandidateSourceResult]) -> list[CandidateSourceResult]:
    deduped: list[CandidateSourceResult] = []
    seen_identities: set[str] = set()
    for result in results:
        normalized = normalize_result(result)
        identity_keys = candidate_identity_keys(normalized)
        if identity_keys & seen_identities:
            continue
        seen_identities.update(identity_keys)
        deduped.append(normalized)
    return deduped


def channel_diagnostics(channel_errors: dict[str, Exception]) -> dict[str, Any]:
    return {
        "channels": {
            channel: {"error_type": type(error).__name__, "message": str(error)}
            for channel, error in channel_errors.items()
        }
    }


def search_run_channel_progress(
    search_run: SearchRun,
) -> dict[str, dict[str, int | str]]:
    progress = search_run_progress(search_run)
    existing = progress.get("channels")
    if not isinstance(existing, dict):
        return {}
    return {
        str(channel): {
            "status": str(details.get("status", "pending")),
            "candidate_count": int(details.get("candidate_count", 0)),
        }
        for channel, details in existing.items()
        if isinstance(details, dict)
    }


def mark_search_failed(
    session: Session,
    search_run_id: str,
    channel_errors: dict[str, Exception],
    *,
    error_message: str = "All selected search channels failed",
    channel_progress: dict[str, dict[str, int | str]] | None = None,
) -> None:
    session.rollback()
    search_run = session.get(SearchRun, search_run_id)
    if search_run is None:
        return
    search_run.status = "failed"
    search_run.completed_at = datetime.now(UTC)
    search_run.run_metadata = {
        **search_run.run_metadata,
        "diagnostics": channel_diagnostics(channel_errors),
        "progress": {
            **search_run_progress(search_run),
            "stage": "failed",
            "active_channel": None,
            "error_message": error_message,
            "channels": channel_progress or search_run_channel_progress(search_run),
        },
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


def search_run_progress(search_run: SearchRun) -> dict[str, Any]:
    progress = search_run.run_metadata.get("progress", {})
    return progress if isinstance(progress, dict) else {}


def update_search_progress(
    session: Session,
    search_run: SearchRun,
    *,
    stage: str,
    completed_channels: int,
    active_channel: str | None,
    channel_progress: dict[str, dict[str, int | str]] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> None:
    search_run.run_metadata = {
        **search_run.run_metadata,
        **({"diagnostics": diagnostics} if diagnostics is not None else {}),
        "progress": {
            "worker": 1,
            "stage": stage,
            "total_channels": len(search_run_channels(search_run)),
            "completed_channels": completed_channels,
            "active_channel": active_channel,
            "channels": channel_progress or search_run_channel_progress(search_run),
        },
    }
    session.add(search_run)
    session.commit()
    session.refresh(search_run)


def candidate_count_for_run(session: Session, search_run_id: str) -> int:
    return len(
        session.exec(
            select(SearchResult.id).where(SearchResult.search_run_id == search_run_id)
        ).all()
    )


def candidate_counts_for_runs(session: Session, search_run_ids: list[str]) -> dict[str, int]:
    if not search_run_ids:
        return {}
    rows = session.exec(
        select(SearchResult.search_run_id, func.count(SearchResult.id))
        .where(SearchResult.search_run_id.in_(search_run_ids))
        .group_by(SearchResult.search_run_id)
    ).all()
    return {str(search_run_id): int(candidate_count) for search_run_id, candidate_count in rows}


def read_search_run(
    session: Session, search_run: SearchRun, *, candidate_count: int | None = None
) -> SearchRunRead:
    return SearchRunRead(
        id=search_run.id,
        job_id=search_run.job_id,
        query=search_run.query,
        provider=search_run.provider,
        channels=search_run_channels(search_run),
        status=search_run.status,
        params=search_run_params(search_run),
        progress=search_run_progress(search_run),
        candidate_count=(
            candidate_count
            if candidate_count is not None
            else candidate_count_for_run(session, search_run.id)
        ),
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
    candidate_counts = candidate_counts_for_runs(session, [search_run.id for search_run in search_runs])
    return [
        read_search_run(
            session,
            search_run,
            candidate_count=candidate_counts.get(search_run.id, 0),
        )
        for search_run in search_runs
    ]


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


def _claim_pending_search_run(session: Session, search_run_id: str) -> SearchRun | None:
    claimed = session.execute(
        update(SearchRun)
        .where(SearchRun.id == search_run_id, SearchRun.status == "pending")
        .values(status="running")
    )
    session.commit()
    search_run = session.get(SearchRun, search_run_id)
    if search_run is None or claimed.rowcount == 0:
        return search_run
    update_search_progress(
        session,
        search_run,
        stage="searching",
        completed_channels=0,
        active_channel=None,
    )
    return search_run


def process_search_run(session: Session, search_run_id: str) -> SearchRun:
    search_run = _claim_pending_search_run(session, search_run_id)
    if search_run is None:
        raise HTTPException(status_code=404, detail="Search run not found")
    if search_run.status != "running":
        return search_run

    try:
        limit = max(int(search_run_params(search_run).get("limit", 10)), 1)
        channels = search_run_channels(search_run)
        channel_errors: dict[str, Exception] = {}
        channel_progress: dict[str, dict[str, int | str]] = {
            channel: {"status": "pending", "candidate_count": 0} for channel in channels
        }
        collected_results: dict[str, list[CandidateSourceResult]] = {}
        connector = get_sourcing_connector()
        for index, channel in enumerate(channels, start=1):
            update_search_progress(
                session,
                search_run,
                stage="searching",
                completed_channels=index - 1,
                active_channel=channel,
                channel_progress=channel_progress,
                diagnostics=channel_diagnostics(channel_errors),
            )
            try:
                channel_results = connector.search_people(
                    search_run.query,
                    {
                        **search_run_params(search_run),
                        "channels": [channel],
                    },
                )
            except Exception as exc:
                session.rollback()
                channel_errors[channel] = exc
                channel_progress[channel] = {
                    "status": "failed",
                    "candidate_count": 0,
                }
            else:
                channel_progress[channel] = {
                    "status": "collected",
                    "candidate_count": 0,
                }
                collected_results[channel] = dedupe_results(channel_results)
            update_search_progress(
                session,
                search_run,
                stage="searching",
                completed_channels=index,
                active_channel=None,
                channel_progress=channel_progress,
                diagnostics=channel_diagnostics(channel_errors),
            )

        selected_results = select_channel_results(collected_results, channels, limit)
        for rank, (channel, result) in enumerate(selected_results, start=1):
            try:
                candidate = upsert_candidate(session, result)
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
                channel_progress[channel]["candidate_count"] += 1
            except Exception as exc:
                session.rollback()
                channel_errors[channel] = exc
                channel_progress[channel] = {
                    "status": "failed",
                    "candidate_count": int(channel_progress[channel]["candidate_count"]),
                }

        for channel in channels:
            if channel not in channel_errors:
                channel_progress[channel]["status"] = "completed"

        persisted_candidate_count = sum(
            int(channel_progress[channel]["candidate_count"]) for channel in channels
        )
        if len(channel_errors) == len(channels) or (
            channel_errors and persisted_candidate_count == 0
        ):
            mark_search_failed(
                session,
                search_run.id,
                channel_errors=channel_errors,
                channel_progress=channel_progress,
            )
            refreshed_search_run = session.get(SearchRun, search_run.id)
            if refreshed_search_run is None:
                raise HTTPException(status_code=404, detail="Search run not found")
            return refreshed_search_run

        update_search_progress(
            session,
            search_run,
            stage="completed",
            completed_channels=len(channels),
            active_channel=None,
            channel_progress=channel_progress,
            diagnostics=channel_diagnostics(channel_errors),
        )
        search_run.status = "completed"
        search_run.completed_at = datetime.now(UTC)
        session.add(search_run)
        session.commit()
        session.refresh(search_run)
        return search_run
    except Exception as exc:
        mark_search_failed(session, search_run.id, {"worker": exc}, error_message="Search run failed")
        refreshed_search_run = session.get(SearchRun, search_run.id)
        if refreshed_search_run is None:
            raise HTTPException(status_code=404, detail="Search run not found") from exc
        return refreshed_search_run


def select_channel_results(
    collected_results: dict[str, list[CandidateSourceResult]],
    channels: list[str],
    limit: int,
) -> list[tuple[str, CandidateSourceResult]]:
    """Reserve one unique candidate per channel before filling the remaining cap."""
    selected: list[tuple[str, CandidateSourceResult]] = []
    seen_identities: set[str] = set()
    positions = {channel: 0 for channel in channels}

    while len(selected) < limit:
        selected_in_round = False
        for channel in channels:
            candidates = collected_results.get(channel, [])
            while positions[channel] < len(candidates):
                candidate = candidates[positions[channel]]
                positions[channel] += 1
                identity_keys = candidate_identity_keys(candidate)
                if identity_keys & seen_identities:
                    continue
                seen_identities.update(identity_keys)
                selected.append((channel, candidate))
                selected_in_round = True
                break
            if len(selected) >= limit:
                break
        if not selected_in_round:
            break
    return selected


@router.post("", response_model=SearchRunRead)
def create_search(
    search_create: SearchCreate, session: Session = Depends(get_session)
) -> SearchRunRead:
    require_persistent_storage_for_writes()
    job = session.get(Job, search_create.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    search_run = SearchRun(
        job_id=search_create.job_id,
        query=search_create.query,
        provider=search_create.provider,
        status="pending",
        run_metadata={
            "params": {
                **search_create.params,
                "region": job.region.strip(),
            },
            "channels": normalize_search_channels(search_create.channels)
            or job.search_channels
            or default_job_search_channels(job.title, job.description),
            "progress": {
                "worker": 1,
                "stage": "queued",
                "total_channels": len(
                    normalize_search_channels(search_create.channels)
                    or job.search_channels
                    or default_job_search_channels(job.title, job.description)
                ),
                "completed_channels": 0,
                "active_channel": None,
                "channels": {
                    channel: {"status": "pending", "candidate_count": 0}
                    for channel in (
                        normalize_search_channels(search_create.channels)
                        or job.search_channels
                        or default_job_search_channels(job.title, job.description)
                    )
                },
            },
        },
    )
    session.add(search_run)
    session.commit()
    session.refresh(search_run)

    return read_search_run(session, search_run)


@router.post("/{search_run_id}/run", response_model=SearchRunDetail)
def run_search(search_run_id: str, session: Session = Depends(get_session)) -> SearchRunDetail:
    search_run = process_search_run(session, search_run_id)
    return get_search_run(search_run.id, session)
