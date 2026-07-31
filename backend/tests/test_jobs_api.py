from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, select

from app.api import jobs
from app.db.models import (
    Candidate,
    CandidateDecision,
    Job,
    PassReason,
    RefinementSuggestion,
    Review,
    ReviewJob,
    Rubric,
    SearchResult,
    SearchRun,
    UserFeedback,
)
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


def test_create_job_generates_rubric(client: TestClient):
    payload = {
        "title": "AI Product Engineer",
        "description": "Build AI prototypes with strong vibe coding.",
        "region": "San Francisco, CA",
        "target_profile_text": "Strong builder, AI-native, product sense.",
        "red_flags_text": "Only traditional backend, no product sense.",
        "search_notes": "Search early AI app builders.",
        "search_channels": ["linkedin", "github", "exa", "brightdata_discover"],
    }

    response = client.post(
        "/api/jobs",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job"]["title"] == payload["title"]
    assert "status" not in data["job"]
    assert data["job"]["region"] == payload["region"]
    assert data["job"]["target_profile_text"] == payload["target_profile_text"]
    assert data["job"]["red_flags_text"] == payload["red_flags_text"]
    assert data["job"]["search_notes"] == payload["search_notes"]
    assert data["job"]["search_channels"] == payload["search_channels"]
    assert data["rubric"]["version"] == 1
    assert len(data["rubric"]["rubric"]["dimensions"]) >= 3


def test_create_job_persists_all_job_fields(client: TestClient, engine: Engine):
    response = client.post(
        "/api/jobs",
        json={
            "title": "PMM Lead",
            "description": "Own product marketing for AI launches.",
            "region": "San Francisco, CA",
            "target_profile_text": "Product marketer with AI launch judgment.",
            "red_flags_text": "Only brand campaigns.",
            "search_notes": "Find product-led PMMs.",
            "search_channels": ["linkedin", "exa", "brightdata_discover"],
        },
    )

    assert response.status_code == 200

    with Session(engine) as session:
        job = session.exec(select(Job)).one()

    assert job.region == "San Francisco, CA"
    assert job.target_profile_text == "Product marketer with AI launch judgment."
    assert job.red_flags_text == "Only brand campaigns."
    assert job.search_notes == "Find product-led PMMs."
    assert job.search_channels == ["linkedin", "exa", "brightdata_discover"]


def test_create_job_defaults_channels_from_role_family(client: TestClient):
    response = client.post(
        "/api/jobs",
        json={
            "title": "Research Scientist",
            "description": "Own applied AI algorithm development.",
        },
    )

    assert response.status_code == 200
    assert response.json()["job"]["search_channels"] == [
        "linkedin",
        "github",
        "openreview",
        "arxiv",
        "exa",
        "brightdata_discover",
    ]


def test_create_job_strips_us_frontier_team_prefix(client: TestClient, engine: Engine):
    response = client.post(
        "/api/jobs",
        json={
            "title": "US Frontier Team - Founding PMM / PMF Discovery Lead",
            "description": "Own PMF discovery.",
            "region": "San Francisco, CA",
        },
    )

    assert response.status_code == 200
    assert response.json()["job"]["title"] == "Founding PMM / PMF Discovery Lead"
    assert response.json()["job"]["region"] == "San Francisco, CA"

    with Session(engine) as session:
        job = session.exec(select(Job)).one()

    assert job.title == "Founding PMM / PMF Discovery Lead"


def test_create_job_rolls_back_when_rubric_insert_fails(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    def fail_rubric(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("rubric insert failed")

    monkeypatch.setattr(jobs, "Rubric", fail_rubric)

    with pytest.raises(RuntimeError, match="rubric insert failed"):
        client.post(
            "/api/jobs",
            json={
                "title": "AI Product Engineer",
                "description": "Build AI prototypes.",
                "target_profile_text": "Strong builder.",
                "red_flags_text": "No product sense.",
                "search_notes": "Search builders.",
            },
        )

    with Session(engine) as session:
        saved_jobs = session.exec(select(Job)).all()

    assert saved_jobs == []


def test_get_job_with_latest_rubric(client: TestClient, engine: Engine):
    response = client.post(
        "/api/jobs",
        json={
            "title": "AI Product Engineer",
            "description": "Build AI prototypes.",
            "target_profile_text": "Strong builder.",
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["id"]

    with Session(engine) as session:
        session.add(
            Rubric(
                job_id=job_id,
                name="Updated rubric",
                criteria=[
                    {
                        "version": 2,
                        "source_hash": "updated",
                        "dimensions": [{"name": "Updated dimension", "weight": 100}],
                    }
                ],
            )
        )
        session.commit()

    detail_response = client.get(f"/api/jobs/{job_id}")

    assert detail_response.status_code == 200
    data = detail_response.json()
    assert data["job"]["id"] == job_id
    assert data["rubric"]["version"] == 2
    assert data["rubric"]["rubric"]["dimensions"][0]["name"] == "Updated dimension"


def test_get_job_with_latest_rubric_404s_for_missing_job(client: TestClient):
    response = client.get("/api/jobs/job_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_list_jobs_returns_created_jobs(client: TestClient):
    response = client.post(
        "/api/jobs",
        json={"title": "AI Product Engineer", "description": "Build demos"},
    )
    assert response.status_code == 200

    list_response = client.get("/api/jobs")

    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "AI Product Engineer"
    assert "status" not in list_response.json()[0]


def test_create_job_reuses_existing_job_with_same_title(client: TestClient, engine: Engine):
    payload = {
        "title": "AI Product Engineer",
        "description": "Build demos.",
        "target_profile_text": "AI-native builder.",
    }

    first_response = client.post("/api/jobs", json=payload)
    second_response = client.post("/api/jobs", json={**payload, "description": "Duplicate draft."})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["job"]["id"] == first_response.json()["job"]["id"]

    with Session(engine) as session:
        saved_jobs = session.exec(select(Job)).all()

    assert len(saved_jobs) == 1
    assert saved_jobs[0].description == "Build demos."


def test_create_job_is_blocked_on_vercel_without_durable_storage(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    from app.core import deployment_guard

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(
        deployment_guard.settings, "database_url", "sqlite:////tmp/talent_sourcing.sqlite3"
    )

    response = client.post(
        "/api/jobs",
        json={"title": "AI Product Engineer", "description": "Build demos"},
    )

    assert response.status_code == 503
    assert "durable storage is configured" in response.json()["detail"]


def test_list_jobs_collapses_legacy_duplicate_titles(client: TestClient, engine: Engine):
    with Session(engine) as session:
        older = Job(title="AI Product Engineer", description="Older duplicate")
        newer = Job(title="AI Product Engineer", description="Newest duplicate")
        other = Job(title="Business Intern", description="Support sourcing")
        session.add(older)
        session.add(newer)
        session.add(other)
        session.commit()

    response = client.get("/api/jobs")

    assert response.status_code == 200
    titles = [job["title"] for job in response.json()]
    assert titles == ["Business Intern", "AI Product Engineer"]
    assert [job["description"] for job in response.json() if job["title"] == "AI Product Engineer"] == [
        "Newest duplicate"
    ]


def test_list_jobs_collapses_us_frontier_team_title_prefix(client: TestClient, engine: Engine):
    with Session(engine) as session:
        older = Job(title="AI Product Engineer", description="Older duplicate")
        newer = Job(title="US Frontier Team - AI Product Engineer", description="Newest duplicate")
        session.add(older)
        session.add(newer)
        session.commit()

    response = client.get("/api/jobs")

    assert response.status_code == 200
    assert [job["title"] for job in response.json()] == ["AI Product Engineer"]


def test_create_job_reuses_existing_job_with_us_frontier_team_prefix(client: TestClient):
    first_response = client.post(
        "/api/jobs",
        json={"title": "US Frontier Team - AI Product Engineer", "description": "Build demos."},
    )
    second_response = client.post(
        "/api/jobs",
        json={"title": "AI Product Engineer", "description": "Duplicate without prefix."},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["job"]["id"] == first_response.json()["job"]["id"]


def test_get_job_404s_when_rubric_missing(client: TestClient, engine: Engine):
    with Session(engine) as session:
        job = Job(title="No Rubric", description="Missing rubric")
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Rubric not found"


def test_delete_job_removes_owned_records_and_preserves_shared_candidates(
    client: TestClient, engine: Engine
):
    with Session(engine) as session:
        job = Job(title="E2E HR Flow", description="Temporary production test job")
        other_job = Job(title="Keep me", description="Unrelated job")
        candidate = Candidate(
            profile_url="https://www.linkedin.com/in/shared-candidate",
            name="Shared Candidate",
        )
        session.add_all([job, other_job, candidate])
        session.flush()

        rubric = Rubric(job_id=job.id, name="Temporary rubric")
        search_run = SearchRun(job_id=job.id, query="temporary search")
        review_job = ReviewJob(job_id=job.id, candidate_id=candidate.id)
        session.add_all([rubric, search_run, review_job])
        session.flush()

        search_result = SearchResult(
            search_run_id=search_run.id,
            candidate_id=candidate.id,
            profile_url=candidate.profile_url,
        )
        review = Review(
            review_job_id=review_job.id,
            summary="Temporary review",
            recommendation="pass",
        )
        session.add_all([search_result, review])
        session.flush()

        decision = CandidateDecision(
            job_id=job.id,
            candidate_id=candidate.id,
            review_id=review.id,
            decision="pass",
        )
        session.add(decision)
        session.flush()

        pass_reason = PassReason(
            candidate_decision_id=decision.id,
            reason_code="temporary",
            reason_text="Temporary reason",
        )
        feedback = UserFeedback(
            job_id=job.id,
            candidate_id=candidate.id,
            candidate_decision_id=decision.id,
            feedback_type="temporary",
            feedback_text="Temporary feedback",
        )
        refinement = RefinementSuggestion(
            job_id=job.id,
            pass_reason_id=pass_reason.id,
            suggestion_type="temporary",
            suggestion_text="Temporary refinement",
        )
        unrelated_feedback = UserFeedback(
            job_id=other_job.id,
            candidate_id=candidate.id,
            feedback_type="keep",
            feedback_text="Unrelated feedback",
        )
        session.add_all([pass_reason, feedback, refinement, unrelated_feedback])
        session.commit()

        job_id = job.id
        candidate_id = candidate.id
        other_job_id = other_job.id

    response = client.delete(f"/api/jobs/{job_id}")

    assert response.status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404

    with Session(engine) as session:
        assert session.get(Candidate, candidate_id) is not None
        assert session.get(Job, other_job_id) is not None
        assert session.exec(select(Rubric).where(Rubric.job_id == job_id)).all() == []
        assert session.exec(select(SearchRun).where(SearchRun.job_id == job_id)).all() == []
        assert session.exec(select(SearchResult)).all() == []
        assert session.exec(select(ReviewJob).where(ReviewJob.job_id == job_id)).all() == []
        assert session.exec(select(Review)).all() == []
        assert session.exec(select(CandidateDecision).where(CandidateDecision.job_id == job_id)).all() == []
        assert session.exec(select(PassReason)).all() == []
        assert session.exec(select(RefinementSuggestion).where(RefinementSuggestion.job_id == job_id)).all() == []
        assert [feedback.feedback_text for feedback in session.exec(select(UserFeedback)).all()] == [
            "Unrelated feedback"
        ]


def test_delete_job_404s_for_missing_job(client: TestClient):
    response = client.delete("/api/jobs/job_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
