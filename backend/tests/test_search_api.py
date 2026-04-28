from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, select

from app.db.models import Candidate, Job, SearchResult, SearchRun
from app.db.session import create_db_engine, get_session
from app.main import app
from app.services.sourcing import CandidateSourceResult


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


def create_job(client: TestClient) -> str:
    response = client.post(
        "/api/jobs",
        json={"title": "Founding PMM", "description": "Find PMF wedge"},
    )
    assert response.status_code == 200
    return str(response.json()["job"]["id"])


def test_search_upserts_candidates_by_linkedin_url(client: TestClient, engine: Engine):
    job_id = create_job(client)

    response = client.post(
        "/api/search",
        json={
            "job_id": job_id,
            "query": "founding PMM AI startup",
            "params": {"limit": 2},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["candidates"]) == 2
    assert data["candidates"][0]["linkedin_url"].startswith("https://www.linkedin.com/in/")

    repeat_response = client.post(
        "/api/search",
        json={
            "job_id": job_id,
            "query": "founding PMM AI startup",
            "params": {"limit": 2},
        },
    )

    assert repeat_response.status_code == 200
    with Session(engine) as session:
        candidates = session.exec(select(Candidate)).all()
    assert len(candidates) == 2


def test_list_search_runs_returns_latest_runs_with_candidate_counts(client: TestClient):
    job_id = create_job(client)
    first_response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "founding PMM AI startup", "params": {"limit": 1}},
    )
    second_response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "AI product marketer", "params": {"limit": 2}},
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get(f"/api/search?job_id={job_id}")

    assert response.status_code == 200
    data = response.json()
    assert [run["query"] for run in data] == ["AI product marketer", "founding PMM AI startup"]
    assert data[0]["candidate_count"] == 2
    assert data[0]["params"] == {"limit": 2}


def test_get_search_run_returns_candidates(client: TestClient):
    job_id = create_job(client)
    create_response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "founding PMM AI startup", "params": {"limit": 1}},
    )
    assert create_response.status_code == 200
    search_run_id = create_response.json()["id"]

    response = client.get(f"/api/search/{search_run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == search_run_id
    assert data["query"] == "founding PMM AI startup"
    assert len(data["candidates"]) == 1


def test_get_search_run_404s_for_missing_run(client: TestClient):
    response = client.get("/api/search/search_run_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Search run not found"


def test_list_search_runs_handles_non_dict_params(client: TestClient, engine: Engine):
    job_id = create_job(client)
    with Session(engine) as session:
        search_run = SearchRun(
            job_id=job_id,
            query="bad params",
            provider="bright_data",
            status="completed",
            run_metadata={"params": "not-a-dict"},
        )
        session.add(search_run)
        session.commit()

    response = client.get(f"/api/search?job_id={job_id}")

    assert response.status_code == 200
    assert response.json()[0]["params"] == {}


def test_search_returns_404_when_job_does_not_exist(client: TestClient):
    response = client.post(
        "/api/search",
        json={
            "job_id": "job_missing",
            "query": "founding PMM AI startup",
            "params": {"limit": 2},
        },
    )

    assert response.status_code == 404


def test_search_marks_run_failed_when_connector_raises(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    job_id = create_job(client)

    class FailingConnector:
        def search_people(self, query, params):  # noqa: ANN001, ANN202
            raise RuntimeError("connector unavailable")

    from app.api import search

    monkeypatch.setattr(search, "get_sourcing_connector", lambda: FailingConnector())

    response = client.post(
        "/api/search",
        json={
            "job_id": job_id,
            "query": "founding PMM AI startup",
            "params": {"limit": 2},
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "connector unavailable"
    with Session(engine) as session:
        search_run = session.exec(select(SearchRun)).one()
    assert search_run.status == "failed"
    assert search_run.run_metadata["error_message"] == "connector unavailable"


def test_search_deduplicates_connector_results_by_canonical_linkedin_url(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    job_id = create_job(client)

    class DuplicateConnector:
        def search_people(self, query, params):  # noqa: ANN001, ANN202
            return [
                CandidateSourceResult(
                    linkedin_url="https://www.linkedin.com/in/example-profile/",
                    name="Example Person",
                    headline="Founding PMM",
                    location="Remote",
                    current_company="ExampleCo",
                    current_title="Founding PMM",
                    raw={"rank": 1},
                ),
                CandidateSourceResult(
                    linkedin_url="https://www.linkedin.com/in/example-profile?trk=people",
                    name="Example Person Duplicate",
                    headline="Duplicate result",
                    location="Remote",
                    current_company="ExampleCo",
                    current_title="Founding PMM",
                    raw={"rank": 2},
                ),
            ]

    from app.api import search

    monkeypatch.setattr(search, "get_sourcing_connector", lambda: DuplicateConnector())

    response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "founding PMM", "params": {"limit": 2}},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["linkedin_url"] == (
        "https://www.linkedin.com/in/example-profile"
    )

    with Session(engine) as session:
        search_results = session.exec(select(SearchResult)).all()
    assert len(search_results) == 1


def test_search_stores_json_unsafe_raw_payload_safely(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    job_id = create_job(client)
    observed_at = datetime(2026, 4, 28, 12, 30, tzinfo=UTC)
    founded_on = date(2024, 1, 2)

    class UnsafeRawConnector:
        def search_people(self, query, params):  # noqa: ANN001, ANN202
            return [
                CandidateSourceResult(
                    linkedin_url="https://www.linkedin.com/in/json-unsafe",
                    name="JSON Unsafe",
                    headline="Has unsafe raw payload",
                    location="Remote",
                    current_company="BytesCo",
                    current_title="PMM",
                    raw={
                        "observed_at": observed_at,
                        "founded_on": founded_on,
                        "score": Decimal("9.75"),
                        "avatar": b"binary-avatar",
                        "tags": {"founder", "builder"},
                        "custom": object(),
                    },
                )
            ]

    from app.api import search

    monkeypatch.setattr(search, "get_sourcing_connector", lambda: UnsafeRawConnector())

    response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "json unsafe"},
    )

    assert response.status_code == 200
    with Session(engine) as session:
        search_result = session.exec(select(SearchResult)).one()
        candidate = session.exec(select(Candidate)).one()

    raw = search_result.raw_data["raw"]
    assert raw["observed_at"] == observed_at.isoformat()
    assert raw["founded_on"] == founded_on.isoformat()
    assert raw["score"] == "9.75"
    assert raw["avatar"] == "binary-avatar"
    assert sorted(raw["tags"]) == ["builder", "founder"]
    assert raw["custom"].startswith("<object object at")
    assert candidate.profile_data["raw"] == raw


def test_mark_search_failed_ignores_missing_search_run(engine: Engine):
    from app.api.search import mark_search_failed

    with Session(engine) as session:
        mark_search_failed(session, "search_run_missing", "missing")

    with Session(engine) as session:
        assert session.exec(select(SearchRun)).all() == []


def test_search_marks_run_failed_when_persistence_fails(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    job_id = create_job(client)

    from app.api import search

    def fail_upsert(session, result):  # noqa: ANN001, ANN202
        raise RuntimeError("candidate persistence failed")

    monkeypatch.setattr(search, "upsert_candidate", fail_upsert)

    response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "founding PMM"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "candidate persistence failed"
    with Session(engine) as session:
        search_run = session.exec(select(SearchRun)).one()
    assert search_run.status == "failed"
    assert search_run.run_metadata["error_message"] == "candidate persistence failed"


def test_json_safe_value_converts_unknown_objects_to_string():
    from app.api.search import json_safe_value

    class UnknownValue:
        def __str__(self) -> str:
            return "unknown-value"

    assert json_safe_value({"value": UnknownValue()}) == {"value": "unknown-value"}


def test_candidate_race_recovery_preserves_prior_search_results(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    from app.api import search

    race_url = "https://www.linkedin.com/in/race-candidate"

    with Session(engine) as session:
        job = Job(title="Founding PMM", description="Find PMF wedge")
        existing_candidate = Candidate(linkedin_url=race_url, name="Existing Candidate")
        session.add(job)
        session.add(existing_candidate)
        session.commit()
        session.refresh(job)
        session.refresh(existing_candidate)

        search_run = SearchRun(
            job_id=job.id,
            query="founding PMM",
            status="running",
        )
        session.add(search_run)
        session.commit()
        session.refresh(search_run)
        search_run_id = search_run.id

        prior_candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/prior-candidate",
            name="Prior Candidate",
        )
        session.add(prior_candidate)
        session.flush()
        session.add(
            SearchResult(
                search_run_id=search_run_id,
                candidate_id=prior_candidate.id,
                linkedin_url=prior_candidate.linkedin_url,
                rank=1,
                raw_data={"raw": {"rank": 1}},
            )
        )

        real_exec = session.exec
        stale_select_used = False

        class EmptyResult:
            def first(self):  # noqa: ANN202
                return None

        def exec_with_stale_race_select(statement):  # noqa: ANN001, ANN202
            nonlocal stale_select_used
            if not stale_select_used:
                stale_select_used = True
                return EmptyResult()
            return real_exec(statement)

        monkeypatch.setattr(session, "exec", exec_with_stale_race_select)

        candidate = search.upsert_candidate(
            session,
            CandidateSourceResult(
                linkedin_url=race_url,
                name="Race Candidate",
                headline="Updated headline",
                location="Remote",
                current_company="RaceCo",
                current_title="PMM",
                raw={"rank": 2},
            ),
        )
        session.add(
            SearchResult(
                search_run_id=search_run_id,
                candidate_id=candidate.id,
                linkedin_url=candidate.linkedin_url,
                rank=2,
                raw_data={"raw": {"rank": 2}},
            )
        )
        session.commit()

    with Session(engine) as session:
        search_results = session.exec(
            select(SearchResult).where(SearchResult.search_run_id == search_run_id)
        ).all()

    assert len(search_results) == 2
