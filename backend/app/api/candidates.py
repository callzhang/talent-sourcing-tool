from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.models import Candidate, CandidateDecision, SearchResult, SearchRun
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


def latest_decision_for_candidate(
    session: Session, candidate_id: str, job_id: str | None
) -> CandidateDecision | None:
    if job_id is None:
        return None
    return session.exec(
        select(CandidateDecision)
        .where(
            CandidateDecision.candidate_id == candidate_id,
            CandidateDecision.job_id == job_id,
        )
        .order_by(CandidateDecision.updated_at.desc(), CandidateDecision.created_at.desc())
    ).first()


def candidate_list_item(
    session: Session, candidate: Candidate, job_id: str | None
) -> CandidateListItem:
    search_result, search_run = latest_search_result_for_candidate(session, candidate.id, job_id)
    latest_decision = latest_decision_for_candidate(session, candidate.id, job_id)
    return CandidateListItem(
        **candidate.model_dump(),
        last_search_run_id=search_run.id if search_run is not None else None,
        last_search_query=search_run.query if search_run is not None else None,
        last_search_rank=search_result.rank if search_result is not None else None,
        latest_decision=latest_decision,
    )


def candidate_list_items(session: Session, job_id: str | None) -> list[CandidateListItem]:
    """Build the queue with a bounded number of database queries.

    The previous implementation issued a search-result and decision lookup for
    every candidate. That becomes visibly slow against the production database.
    """
    candidates = session.exec(select(Candidate).order_by(Candidate.updated_at.desc())).all()
    search_results_query = (
        select(SearchResult, SearchRun)
        .join(SearchRun, SearchResult.search_run_id == SearchRun.id)
        .order_by(SearchResult.created_at.desc())
    )
    if job_id is not None:
        search_results_query = search_results_query.where(SearchRun.job_id == job_id)

    latest_searches: dict[str, tuple[SearchResult, SearchRun]] = {}
    for search_result, search_run in session.exec(search_results_query).all():
        latest_searches.setdefault(search_result.candidate_id, (search_result, search_run))

    latest_decisions: dict[str, CandidateDecision] = {}
    if job_id is not None:
        decisions = session.exec(
            select(CandidateDecision)
            .where(CandidateDecision.job_id == job_id)
            .order_by(CandidateDecision.updated_at.desc(), CandidateDecision.created_at.desc())
        ).all()
        for decision in decisions:
            latest_decisions.setdefault(decision.candidate_id, decision)

    items: list[CandidateListItem] = []
    for candidate in candidates:
        search_result, search_run = latest_searches.get(candidate.id, (None, None))
        if job_id is not None and search_run is None:
            continue
        items.append(
            CandidateListItem(
                **candidate.model_dump(),
                last_search_run_id=search_run.id if search_run is not None else None,
                last_search_query=search_run.query if search_run is not None else None,
                last_search_rank=search_result.rank if search_result is not None else None,
                latest_decision=latest_decisions.get(candidate.id),
            )
        )
    return items


@router.get("", response_model=list[CandidateListItem])
def list_candidates(
    job_id: str | None = None, session: Session = Depends(get_session)
) -> list[CandidateListItem]:
    return candidate_list_items(session, job_id)


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
