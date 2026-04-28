from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.core.config import Settings
from app.db import models
from app.db.init_db import init_db
from app.db.models import Candidate, CandidateDecision, Job, PassReason
from app.db.session import create_db_engine, get_session
from app.schemas import DecisionCreate


def in_memory_engine():
    engine = create_db_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_candidate_linkedin_url_is_unique():
    engine = in_memory_engine()

    with Session(engine) as session:
        session.add(Candidate(linkedin_url="https://www.linkedin.com/in/example", name="A"))
        session.commit()

        session.add(Candidate(linkedin_url="https://www.linkedin.com/in/example", name="B"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        candidates = session.exec(select(Candidate)).all()
        assert len(candidates) == 1
        assert candidates[0].name == "A"


def test_pass_reason_links_to_job_and_candidate_decision():
    engine = in_memory_engine()

    with Session(engine) as session:
        job = Job(title="AI Product Engineer", description="Build AI prototypes")
        candidate = Candidate(linkedin_url="https://www.linkedin.com/in/example", name="A")
        session.add(job)
        session.add(candidate)
        session.commit()
        session.refresh(job)
        session.refresh(candidate)

        decision = CandidateDecision(
            job_id=job.id,
            candidate_id=candidate.id,
            decision="pass",
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)

        reason = PassReason(
            candidate_decision_id=decision.id,
            reason_code="weak_builder_evidence",
            reason_text="No public evidence of building AI prototypes.",
            agent_suggested=True,
            user_edited=False,
        )
        session.add(reason)
        session.commit()

        saved = session.exec(select(PassReason)).one()
        assert saved.reason_code == "weak_builder_evidence"


def test_orphaned_pass_reason_candidate_decision_fails():
    engine = in_memory_engine()

    with Session(engine) as session:
        reason = PassReason(
            candidate_decision_id="decision_missing",
            reason_code="weak_builder_evidence",
            reason_text="No public evidence of building AI prototypes.",
            agent_suggested=True,
            user_edited=False,
        )
        session.add(reason)

        with pytest.raises(IntegrityError):
            session.commit()


def test_default_database_url_is_absolute():
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("sqlite:////")
    assert Path(settings.database_url.removeprefix("sqlite:///")).is_absolute()


def test_database_url_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("TALENT_DATABASE_URL", "sqlite:///override.sqlite3")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///override.sqlite3"


def test_id_factories_use_expected_prefixes():
    assert models.candidate_source_id().startswith("candidate_source_")
    assert models.user_feedback_id().startswith("feedback_")


def test_get_session_yields_session():
    session_generator = get_session()
    session = next(session_generator)
    try:
        assert session is not None
    finally:
        session.close()


def test_init_db_invokes_metadata_create_all(monkeypatch):
    calls = []

    def fake_create_all(engine):  # noqa: ANN001, ANN202
        calls.append(engine)

    monkeypatch.setattr("app.db.init_db.SQLModel.metadata.create_all", fake_create_all)

    init_db()

    assert len(calls) == 1


def test_app_lifespan_initializes_tables_when_enabled(monkeypatch):
    from app.main import app, lifespan

    calls = []

    def fake_init_db():  # noqa: ANN202
        calls.append("init")

    monkeypatch.setattr("app.main.init_db", fake_init_db)
    app.state.create_tables_on_startup = True

    async def run_lifespan() -> None:
        async with lifespan(app):
            calls.append("yielded")

    import asyncio

    asyncio.run(run_lifespan())

    assert calls == ["init", "yielded"]


def test_decision_create_rejects_unknown_decision():
    with pytest.raises(ValidationError, match="decision must be pass or proceed"):
        DecisionCreate(job_id="job_1", candidate_id="candidate_1", decision="maybe")
