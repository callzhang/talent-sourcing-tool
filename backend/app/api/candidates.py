from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.models import Candidate, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateListItem

router = APIRouter(prefix="/candidates", tags=["candidates"])


def latest_search_result_for_candidate(
    session: Session, candidate_id: str, job_id: str | None
) -> tuple[SearchResult | None, SearchRun | None]:
    search_results = session.exec(
        select(SearchResult)
        .where(SearchResult.candidate_id == candidate_id)
        .order_by(SearchResult.created_at.desc())
    ).all()
    for search_result in search_results:
        search_run = session.get(SearchRun, search_result.search_run_id)
        if search_run is None:
            continue
        if job_id is None or search_run.job_id == job_id:
            return search_result, search_run
    return None, None


def candidate_list_item(
    session: Session, candidate: Candidate, job_id: str | None
) -> CandidateListItem:
    search_result, search_run = latest_search_result_for_candidate(session, candidate.id, job_id)
    return CandidateListItem(
        **candidate.model_dump(),
        last_search_run_id=search_run.id if search_run is not None else None,
        last_search_query=search_run.query if search_run is not None else None,
        last_search_rank=search_result.rank if search_result is not None else None,
    )


@router.get("", response_model=list[CandidateListItem])
def list_candidates(
    job_id: str | None = None, session: Session = Depends(get_session)
) -> list[CandidateListItem]:
    candidates = session.exec(select(Candidate).order_by(Candidate.updated_at.desc())).all()
    items = [candidate_list_item(session, candidate, job_id) for candidate in candidates]
    if job_id is not None:
        return [item for item in items if item.last_search_run_id is not None]
    return items


@router.get("/{candidate_id}", response_model=CandidateListItem)
def get_candidate(
    candidate_id: str,
    job_id: str | None = None,
    session: Session = Depends(get_session),
) -> CandidateListItem:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate_list_item(session, candidate, job_id)
