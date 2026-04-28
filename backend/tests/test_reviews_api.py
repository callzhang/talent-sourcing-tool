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


@pytest.mark.parametrize(
    ("review_job_id_key", "wrong_value"),
    [
        ("job_id", "job_wrong"),
        ("candidate_id", "candidate_wrong"),
    ],
)
def test_start_review_rejects_worker_output_for_wrong_job_or_candidate(
    client: TestClient,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    review_job_id_key: str,
    wrong_value: str,
):
    job_id, candidate_id = seed_review_inputs(engine)

    def fake_run_review(self, review_job_id, payload):  # noqa: ANN001, ANN202
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        input_path = workspace / "input.json"
        output_path = workspace / "review.json"
        review = {
            "candidate_id": payload["candidate"]["id"],
            "job_id": payload["job"]["id"],
            "overall_score": 8.5,
            "recommendation": "proceed",
            "decision_summary": "This output is for the wrong entity.",
        }
        review[review_job_id_key] = wrong_value
        return ReviewWorkerResult(
            workspace=workspace,
            input_path=input_path,
            output_path=output_path,
            review=review,
        )

    from app.api import reviews

    monkeypatch.setattr(reviews.ReviewWorker, "run_review", fake_run_review)

    response = client.post(
        "/api/reviews/start",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )

    assert response.status_code == 502
    assert "does not match review job" in response.json()["detail"]

    with Session(engine) as session:
        review_job = session.exec(select(ReviewJob)).one()
        saved_reviews = session.exec(select(Review)).all()

    assert review_job.status == "failed"
    assert review_job.error_message is not None
    assert "does not match review job" in review_job.error_message
    assert saved_reviews == []


def test_start_review_404s_for_missing_job_or_candidate_and_400s_without_rubric(
    client: TestClient, engine: Engine
):
    response = client.post(
        "/api/reviews/start",
        json={"candidate_id": "candidate_missing", "job_id": "job_missing"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        session.exec(select(Rubric)).all()
        rubric = session.exec(select(Rubric)).one()
        session.delete(rubric)
        session.commit()

    missing_candidate_response = client.post(
        "/api/reviews/start",
        json={"candidate_id": "candidate_missing", "job_id": job_id},
    )
    assert missing_candidate_response.status_code == 404
    assert missing_candidate_response.json()["detail"] == "Candidate not found"

    no_rubric_response = client.post(
        "/api/reviews/start",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )
    assert no_rubric_response.status_code == 400
    assert no_rubric_response.json()["detail"] == "Job has no rubric"


def test_start_review_marks_failed_when_worker_raises(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
):
    job_id, candidate_id = seed_review_inputs(engine)

    def fail_run_review(self, review_job_id, payload):  # noqa: ANN001, ANN202
        raise RuntimeError("worker unavailable")

    from app.api import reviews

    monkeypatch.setattr(reviews.ReviewWorker, "run_review", fail_run_review)

    response = client.post(
        "/api/reviews/start",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "worker unavailable"
    with Session(engine) as session:
        review_job = session.exec(select(ReviewJob)).one()
    assert review_job.status == "failed"
    assert review_job.error_message == "worker unavailable"


def test_review_helpers_cover_defensive_paths(engine: Engine):
    from app.api.reviews import (
        _normalized_reason_codes,
        mark_review_job_failed,
        pass_reasons_for_job,
        validate_review_identity,
    )

    with Session(engine) as session:
        assert pass_reasons_for_job(session, "job_missing") == []
        assert _normalized_reason_codes("not-a-list") == ()
        mark_review_job_failed(session, "review_job_missing", "missing")

        job = Job(title="AI Product Engineer", description="Build demos")
        candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/helper",
            name="Helper Candidate",
            profile_data={},
        )
        session.add(job)
        session.add(candidate)
        session.commit()
        session.refresh(job)
        session.refresh(candidate)
        review_job = ReviewJob(job_id="job_other", candidate_id=candidate.id, status="running")

        with pytest.raises(ValueError, match="does not match current job"):
            validate_review_identity(
                review_data={"job_id": job.id, "candidate_id": candidate.id},
                review_job=review_job,
                job=job,
                candidate=candidate,
            )


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
                "dimension_scores": [
                    {
                        "name": "Builder Evidence",
                        "score": 35,
                        "reason_code": "weak_builder_evidence",
                    }
                ],
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


def test_get_latest_review_for_candidate_and_job(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        first_job = ReviewJob(job_id=job_id, candidate_id=candidate_id, status="completed")
        session.add(first_job)
        session.commit()
        session.refresh(first_job)
        session.add(
            Review(
                review_job_id=first_job.id,
                summary="Older summary.",
                evidence=[],
                recommendation="pass",
                score=4.0,
                raw_review={"decision_summary": "Older summary.", "overall_score": 4.0},
            )
        )
        second_job = ReviewJob(job_id=job_id, candidate_id=candidate_id, status="completed")
        session.add(second_job)
        session.commit()
        session.refresh(second_job)
        session.add(
            Review(
                review_job_id=second_job.id,
                summary="Newer summary.",
                evidence=[{"label": "launch", "detail": "Led AI launch"}],
                recommendation="proceed",
                score=8.0,
                raw_review={
                    "decision_summary": "Newer summary.",
                    "overall_score": 8.0,
                    "recommendation": "proceed",
                    "evidence": [{"label": "launch", "detail": "Led AI launch"}],
                },
            )
        )
        session.commit()

    response = client.get(f"/api/reviews/latest?job_id={job_id}&candidate_id={candidate_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Newer summary."
    assert data["review"]["recommendation"] == "proceed"
    assert data["review"]["evidence"][0]["label"] == "launch"


def test_get_latest_review_returns_null_when_absent(client: TestClient, engine: Engine):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.get(f"/api/reviews/latest?job_id={job_id}&candidate_id={candidate_id}")

    assert response.status_code == 200
    assert response.json() is None


def test_get_latest_review_404s_for_missing_job_or_candidate(
    client: TestClient, engine: Engine
):
    job_id, _candidate_id = seed_review_inputs(engine)

    missing_job_response = client.get(
        "/api/reviews/latest?job_id=job_missing&candidate_id=candidate_missing"
    )
    assert missing_job_response.status_code == 404
    assert missing_job_response.json()["detail"] == "Job not found"

    missing_candidate_response = client.get(
        f"/api/reviews/latest?job_id={job_id}&candidate_id=candidate_missing"
    )
    assert missing_candidate_response.status_code == 404
    assert missing_candidate_response.json()["detail"] == "Candidate not found"


def test_get_latest_review_returns_null_when_review_job_has_no_review(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        session.add(ReviewJob(job_id=job_id, candidate_id=candidate_id, status="completed"))
        session.commit()

    response = client.get(f"/api/reviews/latest?job_id={job_id}&candidate_id={candidate_id}")

    assert response.status_code == 200
    assert response.json() is None


def test_read_review_404s_when_review_job_is_missing(engine: Engine):
    from app.api.reviews import read_review

    with Session(engine) as session:
        review = Review(
            review_job_id="review_job_missing",
            summary="orphan review",
            evidence=[],
            recommendation="pass",
            score=1,
            raw_review={},
        )

        with pytest.raises(Exception, match="404: Review job not found"):
            read_review(session, review)


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


def test_refinement_suggestions_endpoint_404s_for_missing_job(client: TestClient):
    response = client.get("/api/reviews/refinements?job_id=job_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_pass_decision_does_not_create_refinement_for_unknown_reason_code(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "decision": "pass",
            "pass_reason_code": "manual_pass",
            "pass_reason_text": "Manually passed for context not covered by the rubric.",
        },
    )

    assert response.status_code == 200

    with Session(engine) as session:
        assert session.exec(select(PassReason)).one().reason_code == "manual_pass"
        assert session.exec(select(RefinementSuggestion)).all() == []


def test_pass_decision_dedupes_pending_refinement_suggestions(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/another",
            name="Another Candidate",
            profile_data={},
        )
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        other_candidate_id = candidate.id

    payload = {
        "job_id": job_id,
        "decision": "pass",
        "pass_reason_code": "weak_builder_evidence",
        "pass_reason_text": "No public evidence of shipping AI prototypes.",
    }

    first_response = client.post(
        "/api/reviews/decision",
        json={**payload, "candidate_id": candidate_id},
    )
    second_response = client.post(
        "/api/reviews/decision",
        json={**payload, "candidate_id": other_candidate_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    with Session(engine) as session:
        pass_reasons = session.exec(select(PassReason)).all()
        suggestions = session.exec(select(RefinementSuggestion)).all()

    assert len(pass_reasons) == 2
    assert len(suggestions) == 1
    assert suggestions[0].status == "pending"
    assert suggestions[0].suggestion_type == "rubric_adjustment"
    assert suggestions[0].suggestion_metadata == {"reason_codes": ["weak_builder_evidence"]}


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


def test_decision_404s_for_missing_job_candidate_review_or_review_job(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)

    missing_job_response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": "job_missing",
            "candidate_id": candidate_id,
            "decision": "proceed",
        },
    )
    assert missing_job_response.status_code == 404
    assert missing_job_response.json()["detail"] == "Job not found"

    missing_candidate_response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": "candidate_missing",
            "decision": "proceed",
        },
    )
    assert missing_candidate_response.status_code == 404
    assert missing_candidate_response.json()["detail"] == "Candidate not found"

    missing_review_response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "review_id": "review_missing",
            "decision": "proceed",
        },
    )
    assert missing_review_response.status_code == 404
    assert missing_review_response.json()["detail"] == "Review not found"

    with Session(engine) as session:
        from app.api.reviews import create_decision
        from app.schemas import DecisionCreate

        orphan_review = Review(
            id="review_orphan",
            review_job_id="review_job_missing",
            summary="orphan review",
            evidence=[],
            recommendation="proceed",
            score=8,
            raw_review={},
        )

        real_get = session.get

        def get_with_orphan_review(model, object_id):  # noqa: ANN001, ANN202
            if model is Review and object_id == "review_orphan":
                return orphan_review
            if model is ReviewJob and object_id == "review_job_missing":
                return None
            return real_get(model, object_id)

        session.get = get_with_orphan_review  # type: ignore[method-assign]
        with pytest.raises(Exception, match="404: Review job not found"):
            create_decision(
                DecisionCreate(
                    job_id=job_id,
                    candidate_id=candidate_id,
                    review_id="review_orphan",
                    decision="proceed",
                ),
                session,
            )


def test_decision_rejects_review_owned_by_different_candidate(
    client: TestClient, engine: Engine
):
    job_id, candidate_id = seed_review_inputs(engine)
    with Session(engine) as session:
        other_candidate = Candidate(
            linkedin_url="https://www.linkedin.com/in/other-candidate",
            name="Other Candidate",
            profile_data={},
        )
        session.add(other_candidate)
        session.commit()
        session.refresh(other_candidate)
        review_job = ReviewJob(
            job_id=job_id,
            candidate_id=other_candidate.id,
            status="completed",
        )
        session.add(review_job)
        session.commit()
        session.refresh(review_job)
        review = Review(
            review_job_id=review_job.id,
            summary="Other candidate review.",
            evidence=[],
            recommendation="proceed",
            score=8.0,
            raw_review={"decision_summary": "Other candidate review."},
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        review_id = review.id

    response = client.post(
        "/api/reviews/decision",
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "review_id": review_id,
            "decision": "proceed",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Review does not belong to job and candidate"

    with Session(engine) as session:
        assert session.exec(select(CandidateDecision)).all() == []
