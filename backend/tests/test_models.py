from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import Candidate, Job, PassReason


def test_candidate_linkedin_url_is_unique():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Candidate(linkedin_url="https://www.linkedin.com/in/example", name="A"))
        session.commit()

        session.add(Candidate(linkedin_url="https://www.linkedin.com/in/example", name="B"))
        try:
            session.commit()
            raise AssertionError("duplicate LinkedIn URL should fail")
        except Exception:
            session.rollback()

        candidates = session.exec(select(Candidate)).all()
        assert len(candidates) == 1
        assert candidates[0].name == "A"


def test_pass_reason_links_to_job_and_candidate_decision():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        job = Job(title="AI Product Engineer", description="Build AI prototypes")
        session.add(job)
        session.commit()
        session.refresh(job)

        reason = PassReason(
            candidate_decision_id="decision_1",
            reason_code="weak_builder_evidence",
            reason_text="No public evidence of building AI prototypes.",
            agent_suggested=True,
            user_edited=False,
        )
        session.add(reason)
        session.commit()

        saved = session.exec(select(PassReason)).one()
        assert saved.reason_code == "weak_builder_evidence"
