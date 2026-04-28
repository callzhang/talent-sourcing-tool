from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, select

from app.db.models import (
    Candidate,
    CandidateDecision,
    Job,
    PassReason,
    RefinementSuggestion,
    Review,
    ReviewJob,
    Rubric,
)
from app.db.session import create_db_engine, get_session
from app.main import app
from app.services.review_worker import ReviewWorkerResult


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


def seed_review_inputs(engine: Engine) -> tuple[str, str]:
    with Session(engine) as session:
        job = Job(title="AI Product Engineer", description="Build AI prototypes")
        candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/example",
            name="Example Candidate",
            profile_data={"current_title": "Founding Engineer"},
        )
        session.add(job)
        session.add(candidate)
        session.commit()
        session.refresh(job)
        session.refresh(candidate)
        session.add(
            Rubric(
                job_id=job.id,
                name="Default rubric",
                criteria=[{"version": 1, "dimensions": [{"name": "Builder evidence"}]}],
            )
        )
        session.commit()
        return job.id, candidate.id


def test_start_review_stores_review_and_completed_review_job(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    job_id, candidate_id = seed_review_inputs(engine)

    def fake_run_review(self, review_job_id, payload):  # noqa: ANN001, ANN202
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        input_path = workspace / "input.json"
        output_path = workspace / "review.json"
        input_path.write_text("{}")
        output_path.write_text("{}")
        return ReviewWorkerResult(
            workspace=workspace,
            input_path=input_path,
            output_path=output_path,
            review={
                "candidate_id": payload["candidate"]["id"],
                "job_id": payload["job"]["id"],
                "overall_score": 8.5,
                "recommendation": "proceed",
                "decision_summary": "Strong builder evidence.",
                "evidence": [{"label": "prototype", "detail": "Built AI apps"}],
            },
        )

    from app.api import reviews

    monkeypatch.setattr(reviews.ReviewWorker, "run_review", fake_run_review)

    response = client.post(
        "/api/reviews/start",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["review_job_id"].startswith("review_job_")
    assert data["review_id"].startswith("review_")
    assert data["review"]["overall_score"] == 8.5
    assert data["review"]["recommendation"] == "proceed"

    with Session(engine) as session:
        review_job = session.exec(select(ReviewJob)).one()
        review = session.exec(select(Review)).one()

    assert review_job.status == "completed"
    assert review_job.workspace_path == str(tmp_path / "workspace")
    assert review_job.input_path == str(tmp_path / "workspace" / "input.json")
    assert review_job.output_path == str(tmp_path / "workspace" / "review.json")
    assert review.review_job_id == review_job.id
    assert review.summary == "Strong builder evidence."
    assert review.score == 8.5


def test_start_review_marks_job_failed_when_worker_output_breaks_persistence(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    job_id, candidate_id = seed_review_inputs(engine)

    def fake_run_review(self, review_job_id, payload):  # noqa: ANN001, ANN202
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        input_path = workspace / "input.json"
        output_path = workspace / "review.json"
        return ReviewWorkerResult(
            workspace=workspace,
            input_path=input_path,
            output_path=output_path,
            review={
                "candidate_id": payload["candidate"]["id"],
                "job_id": payload["job"]["id"],
                "overall_score": "not-a-number",
                "recommendation": "proceed",
                "decision_summary": "Invalid score should fail persistence.",
            },
        )

    from app.api import reviews

    monkeypatch.setattr(reviews.ReviewWorker, "run_review", fake_run_review)

    response = client.post(
        "/api/reviews/start",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )

    assert response.status_code == 502
    assert "not-a-number" in response.json()["detail"]

    with Session(engine) as session:
        review_job = session.exec(select(ReviewJob)).one()
        saved_reviews = session.exec(select(Review)).all()

    assert review_job.status == "failed"
    assert review_job.error_message is not None
    assert "not-a-number" in review_job.error_message
    assert saved_reviews == []


def test_draft_pass_reason_endpoint_returns_draft(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        review_job = ReviewJob(job_id=job_id, candidate_id=candidate_id, status="completed")
        session.add(review_job)
        session.commit()
        session.refresh(review_job)
        review = Review(
            review_job_id=review_job.id,
            summary="Weak builder evidence.",
            evidence=[],
            recommendation="pass",
            score=4.0,
            raw_review={
                "risks": ["No public evidence of shipping AI products"],
                "dimension_scores": [{"name": "Builder Evidence", "score": 35}],
            },
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        review_id = review.id

    response = client.get(f"/api/reviews/{review_id}/draft-pass-reason")

    assert response.status_code == 200
    data = response.json()
    assert data["reason_code"] == "weak_builder_evidence"
    assert data["evidence"] == ["No public evidence of shipping AI products"]


def test_draft_pass_reason_endpoint_404s_for_missing_review(client: TestClient):
    response = client.get("/api/reviews/review_missing/draft-pass-reason")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


def test_draft_pass_reason_endpoint_handles_malformed_raw_review(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        review_job = ReviewJob(job_id=job_id, candidate_id=candidate_id, status="completed")
        session.add(review_job)
        session.commit()
        session.refresh(review_job)
        review = Review(
            review_job_id=review_job.id,
            summary="Malformed review.",
            evidence=[],
            recommendation="pass",
            score=4.0,
            raw_review={
                "risks": [None, {"detail": "hidden object"}, "Visible risk"],
                "dimension_scores": None,
            },
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        review_id = review.id

    response = client.get(f"/api/reviews/{review_id}/draft-pass-reason")

    assert response.status_code == 200
    data = response.json()
    assert data["reason_code"] == "insufficient_public_evidence"
    assert data["evidence"] == ["Visible risk"]


def test_pass_requires_pass_reason(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "pass",
        },
    )

    assert response.status_code == 422

    with Session(engine) as session:
        assert session.exec(select(CandidateDecision)).all() == []
        assert session.exec(select(PassReason)).all() == []


def test_pass_rejects_blank_pass_reason_text(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "pass",
            "pass_reason_text": "   ",
        },
    )

    assert response.status_code == 422

    with Session(engine) as session:
        assert session.exec(select(CandidateDecision)).all() == []
        assert session.exec(select(PassReason)).all() == []


def test_pass_decision_persists_pass_reason_and_refinement_suggestions(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "pass",
            "notes": "Not enough direct build evidence.",
            "decided_by": "test-user",
            "pass_reason_code": "weak_builder_evidence",
            "pass_reason_text": "No public evidence of shipping AI prototypes.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "pass"
    assert data["candidate_id"] == candidate_id

    with Session(engine) as session:
        decision = session.exec(select(CandidateDecision)).one()
        pass_reason = session.exec(select(PassReason)).one()
        suggestion = session.exec(select(RefinementSuggestion)).one()

    assert decision.job_id == job_id
    assert decision.candidate_id == candidate_id
    assert decision.notes == "Not enough direct build evidence."
    assert pass_reason.candidate_decision_id == decision.id
    assert pass_reason.reason_code == "weak_builder_evidence"
    assert pass_reason.reason_text == "No public evidence of shipping AI prototypes."
    assert pass_reason.agent_suggested is False
    assert pass_reason.user_edited is True
    assert suggestion.job_id == job_id
    assert suggestion.pass_reason_id == pass_reason.id
    assert suggestion.suggestion_type == "rubric_adjustment"
    assert suggestion.status == "pending"
    assert suggestion.suggestion_metadata == {"reason_codes": ["weak_builder_evidence"]}


def test_refinement_suggestions_endpoint_lists_persisted_suggestions(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)
    client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "pass",
            "pass_reason_code": "weak_builder_evidence",
            "pass_reason_text": "No public evidence of shipping AI prototypes.",
        },
    )

    response = client.get(f"/api/reviews/refinements?job_id={job_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_id"] == job_id
    assert data[0]["suggestion_type"] == "rubric_adjustment"


def test_proceed_decision_creates_candidate_decision(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "proceed",
            "notes": "Move to recruiter screen.",
            "decided_by": "test-user",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "proceed"
    assert data["candidate_id"] == candidate_id

    with Session(engine) as session:
        decision = session.exec(select(CandidateDecision)).one()
        pass_reasons = session.exec(select(PassReason)).all()

    assert decision.job_id == job_id
    assert decision.candidate_id == candidate_id
    assert decision.notes == "Move to recruiter screen."
    assert decision.decided_by == "test-user"
    assert pass_reasons == []
