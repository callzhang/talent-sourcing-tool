from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel

from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import create_db_engine, get_session
from app.main import app


def test_list_candidates_filters_to_searched_candidates(client: TestClient, engine: Engine):
    job_id, candidate_id, _unsearched_candidate_id = seed_candidates(engine)

    response = client.get(f"/api/candidates?job_id={job_id}")

    assert response.status_code == 200
    data = response.json()
    assert [candidate["id"] for candidate in data] == [candidate_id]
    assert data[0]["last_search_rank"] == 1
    assert data[0]["last_search_query"] == "AI product marketer"


def test_get_candidate_returns_candidate_detail(client: TestClient, engine: Engine):
    job_id, candidate_id, _unsearched_candidate_id = seed_candidates(engine)

    response = client.get(f"/api/candidates/{candidate_id}?job_id={job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == candidate_id
    assert data["linkedin_url"] == "https://www.linkedin.com/in/searched"
    assert data["last_search_query"] == "AI product marketer"


def test_get_candidate_404s_for_missing_candidate(client: TestClient):
    response = client.get("/api/candidates/candidate_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"


def seed_candidates(engine: Engine) -> tuple[str, str, str]:
    with Session(engine) as session:
        job = Job(title="PMM", description="Product marketing")
        searched_candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/searched",
            name="Searched Candidate",
            headline="AI PMM",
            location="Remote",
            current_company="LaunchCo",
            profile_data={"current_title": "PMM"},
        )
        unsearched_candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/unsearched",
            name="Unsearched Candidate",
            profile_data={},
        )
        session.add(job)
        session.add(searched_candidate)
        session.add(unsearched_candidate)
        session.commit()
        session.refresh(job)
        session.refresh(searched_candidate)
        session.refresh(unsearched_candidate)
        search_run = SearchRun(
            job_id=job.id,
            query="AI product marketer",
            provider="bright_data",
            status="completed",
            run_metadata={"params": {"limit": 10}},
        )
        session.add(search_run)
        session.commit()
        session.refresh(search_run)
        session.add(
            SearchResult(
                search_run_id=search_run.id,
                candidate_id=searched_candidate.id,
                linkedin_url=searched_candidate.linkedin_url,
                title="PMM",
                snippet="AI PMM",
                rank=1,
                raw_data={},
            )
        )
        session.commit()
        return job.id, searched_candidate.id, unsearched_candidate.id


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine: Engine) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.state.create_tables_on_startup = False
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.create_tables_on_startup = True
