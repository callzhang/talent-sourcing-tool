from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, select

from app.db.models import Candidate, SearchRun
from app.db.session import create_db_engine, get_session
from app.main import app


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
