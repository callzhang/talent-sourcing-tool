from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.core.config import Settings
from app.db.models import Candidate, CandidateDecision, Job, PassReason
from app.db.session import create_db_engine


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
