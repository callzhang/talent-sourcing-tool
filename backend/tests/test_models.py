from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.core.config import Settings
from app.db import models
from app.db.init_db import init_db, migrate_existing_sqlite_schema
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


def test_migrate_existing_sqlite_schema_adds_job_profile_columns(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'legacy.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE job (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE reviewjob (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    candidate_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    workspace_path VARCHAR,
                    error_message VARCHAR,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME
                )
                """
            )
        )

    migrate_existing_sqlite_schema(engine)

    with engine.begin() as connection:
        job_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(job)")).all()
        }
        review_job_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(reviewjob)")).all()
        }

    assert {"region", "target_profile_text", "red_flags_text", "search_notes", "search_channels"}.issubset(
        job_columns
    )
    assert {"input_path", "output_path"}.issubset(review_job_columns)


def test_migrate_existing_sqlite_schema_is_idempotent(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'current.sqlite3'}")
    SQLModel.metadata.create_all(engine)

    migrate_existing_sqlite_schema(engine)
    migrate_existing_sqlite_schema(engine)

    with engine.begin() as connection:
        job_columns = [
            row[1] for row in connection.execute(text("PRAGMA table_info(job)")).all()
        ]
        review_job_columns = [
            row[1] for row in connection.execute(text("PRAGMA table_info(reviewjob)")).all()
        ]

    assert job_columns.count("target_profile_text") == 1
    assert review_job_columns.count("input_path") == 1


def test_migrate_existing_sqlite_schema_normalizes_job_titles(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'normalized-titles.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE job (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    region TEXT NOT NULL DEFAULT '',
                    status VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE reviewjob (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    candidate_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    workspace_path VARCHAR,
                    error_message VARCHAR,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job
                (id, title, description, region, status, created_at, updated_at)
                VALUES
                ('job_1', 'US Frontier Team - Founding PMM / PMF Discovery Lead', 'Own PMF discovery.', 'San Francisco, CA', 'draft', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )

    migrate_existing_sqlite_schema(engine)

    with engine.begin() as connection:
        row = connection.execute(text("SELECT title, region FROM job WHERE id = 'job_1'")).one()

    assert row == ("Founding PMM / PMF Discovery Lead", "San Francisco, CA")


def test_migrate_existing_sqlite_schema_backfills_search_run_channels(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'legacy-runs.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE job (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    target_profile_text TEXT NOT NULL DEFAULT '',
                    red_flags_text TEXT NOT NULL DEFAULT '',
                    search_notes TEXT NOT NULL DEFAULT '',
                    search_channels JSON NOT NULL DEFAULT '[]',
                    status VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE searchrun (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    query VARCHAR NOT NULL,
                    provider VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    metadata JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE reviewjob (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    candidate_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    workspace_path VARCHAR,
                    error_message VARCHAR,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job
                (id, title, description, search_channels, status, created_at, updated_at)
                VALUES
                ('job_1', 'Founding PMM', 'Own product marketing for AI launch.', '["linkedin","exa"]', 'draft', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO searchrun
                (id, job_id, query, provider, status, metadata, created_at)
                VALUES
                (:id, :job_id, :query, :provider, :status, :metadata, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": "search_run_1",
                "job_id": "job_1",
                "query": "founding PMM",
                "provider": "bright_data",
                "status": "completed",
                "metadata": '{"params":{"limit":10}}',
            },
        )

    migrate_existing_sqlite_schema(engine)

    with engine.begin() as connection:
        metadata = connection.execute(
            text("SELECT metadata FROM searchrun WHERE id = 'search_run_1'")
        ).scalar_one()

    assert '"channels": ["linkedin", "exa", "brightdata_discover"]' in str(metadata)


def test_migrate_existing_sqlite_schema_appends_brightdata_discover_to_run_channels(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'existing-runs.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE job (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    target_profile_text TEXT NOT NULL DEFAULT '',
                    red_flags_text TEXT NOT NULL DEFAULT '',
                    search_notes TEXT NOT NULL DEFAULT '',
                    search_channels JSON NOT NULL DEFAULT '[]',
                    status VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE searchrun (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    query VARCHAR NOT NULL,
                    provider VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    metadata JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE reviewjob (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    candidate_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    workspace_path VARCHAR,
                    error_message VARCHAR,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job
                (id, title, description, search_channels, status, created_at, updated_at)
                VALUES
                ('job_1', 'Founding PMM', 'Own product marketing for AI launch.', '["linkedin","exa","brightdata_discover"]', 'draft', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO searchrun
                (id, job_id, query, provider, status, metadata, created_at)
                VALUES
                (:id, :job_id, :query, :provider, :status, :metadata, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": "search_run_1",
                "job_id": "job_1",
                "query": "founding PMM",
                "provider": "bright_data",
                "status": "completed",
                "metadata": '{"channels":["linkedin","exa"],"params":{"limit":10}}',
            },
        )

    migrate_existing_sqlite_schema(engine)

    with engine.begin() as connection:
        metadata = connection.execute(
            text("SELECT metadata FROM searchrun WHERE id = 'search_run_1'")
        ).scalar_one()

    assert '"channels": ["linkedin", "exa", "brightdata_discover"]' in str(metadata)


def test_migrate_existing_schema_ignores_non_sqlite_engine():
    class Dialect:
        name = "postgresql"

    class NonSqliteEngine:
        dialect = Dialect()

    migrate_existing_sqlite_schema(NonSqliteEngine())  # type: ignore[arg-type]


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
