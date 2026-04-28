from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import Job, Rubric
from app.db.session import get_session
from app.schemas import JobCreate, JobRead, JobWithRubric, RubricRead
from app.services.rubric import rubric_to_json

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def read_rubric(rubric: Rubric) -> RubricRead:
    rubric_payload = rubric.criteria[0] if rubric.criteria else {}
    return RubricRead(
        id=rubric.id,
        job_id=rubric.job_id,
        version=int(rubric_payload.get("version", 1)),
        source_hash=str(rubric_payload.get("source_hash", "")),
        rubric={"dimensions": rubric_payload.get("dimensions", [])},
        created_at=rubric.created_at,
        updated_at=rubric.updated_at,
    )


@router.post("", response_model=JobWithRubric)
def create_job(job_create: JobCreate, session: Session = Depends(get_session)) -> JobWithRubric:
    job = Job(title=job_create.title, description=job_create.description)
    session.add(job)
    session.commit()
    session.refresh(job)

    rubric_payload = json.loads(rubric_to_json(job_create))
    rubric = Rubric(
        job_id=job.id,
        name=f"{job.title} Rubric",
        criteria=[rubric_payload],
    )
    session.add(rubric)
    session.commit()
    session.refresh(rubric)

    return JobWithRubric(job=JobRead.model_validate(job), rubric=read_rubric(rubric))


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)) -> list[JobRead]:
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return [JobRead.model_validate(job) for job in jobs]
