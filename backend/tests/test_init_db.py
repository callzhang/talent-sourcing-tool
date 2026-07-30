from pathlib import Path

from sqlmodel import Session, SQLModel, select

from app.db.init_db import init_db, seed_default_jobs
from app.db.models import Job, Rubric
from app.db.session import create_db_engine


def test_seed_default_jobs_populates_empty_database(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'seed.sqlite3'}")
    SQLModel.metadata.create_all(engine)

    seed_default_jobs(engine)

    with Session(engine) as session:
        jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
        rubrics = session.exec(select(Rubric)).all()

    assert len(jobs) >= 3
    assert {job.title for job in jobs} >= {
        "L5 技术总监",
        "Founding PMM / PMF Discovery Lead",
        "AI Product Engineer",
    }
    assert len(rubrics) >= 3


def test_seed_default_jobs_is_idempotent(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'idempotent.sqlite3'}")
    SQLModel.metadata.create_all(engine)

    seed_default_jobs(engine)
    seed_default_jobs(engine)

    with Session(engine) as session:
        jobs = session.exec(select(Job)).all()
        rubrics = session.exec(select(Rubric)).all()

    assert len(jobs) == 3
    assert len(rubrics) == 3


def test_init_db_seeds_default_jobs_when_creating_schema(monkeypatch, tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'init.sqlite3'}"
    monkeypatch.setattr("app.db.init_db.engine", create_db_engine(database_url))

    init_db()

    with Session(create_db_engine(database_url)) as session:
        jobs = session.exec(select(Job)).all()

    assert {job.title for job in jobs} >= {
        "L5 技术总监",
        "Founding PMM / PMF Discovery Lead",
        "AI Product Engineer",
    }
