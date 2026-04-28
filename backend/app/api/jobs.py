from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.models import Job, Rubric
from app.db.session import get_session
from app.schemas import JobCreate, JobRead, JobWithRubric, RubricRead
from app.services.job_titles import job_title_key, normalize_job_title
from app.services.rubric import rubric_to_json
from app.services.sourcing import default_job_search_channels, normalize_search_channels

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


def read_job(job: Job) -> JobRead:
    return JobRead.model_validate(job.model_copy(update={"title": normalize_job_title(job.title)}))


@router.post("", response_model=JobWithRubric)
def create_job(job_create: JobCreate, session: Session = Depends(get_session)) -> JobWithRubric:
    normalized_title = normalize_job_title(job_create.title)
    title_key = job_title_key(normalized_title)

    with session.begin():
        existing_jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
        for existing_job in existing_jobs:
            if job_title_key(existing_job.title) == title_key:
                rubric = session.exec(
                    select(Rubric)
                    .where(Rubric.job_id == existing_job.id)
                    .order_by(Rubric.created_at.desc())
                ).first()
                if rubric is None:
                    raise HTTPException(status_code=409, detail="Existing job has no rubric")
                return JobWithRubric(job=read_job(existing_job), rubric=read_rubric(rubric))

        rubric_payload = json.loads(rubric_to_json(job_create))
        job = Job(
            title=normalized_title,
            description=job_create.description,
            region=job_create.region.strip(),
            target_profile_text=job_create.target_profile_text,
            red_flags_text=job_create.red_flags_text,
            search_notes=job_create.search_notes,
            search_channels=normalize_search_channels(job_create.search_channels)
            or default_job_search_channels(normalized_title, job_create.description),
        )
        session.add(job)
        session.flush()
        rubric = Rubric(
            job_id=job.id,
            name=f"{job.title} Rubric",
            criteria=[rubric_payload],
        )
        session.add(rubric)

    session.refresh(job)
    session.refresh(rubric)

    return JobWithRubric(job=read_job(job), rubric=read_rubric(rubric))


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)) -> list[JobRead]:
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    unique_jobs: list[Job] = []
    seen_titles: set[str] = set()
    for job in jobs:
        title_key = job_title_key(job.title)
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        unique_jobs.append(job)
    return [read_job(job) for job in unique_jobs]


@router.get("/{job_id}", response_model=JobWithRubric)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobWithRubric:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    rubric = session.exec(
        select(Rubric).where(Rubric.job_id == job.id).order_by(Rubric.created_at.desc())
    ).first()
    if rubric is None:
        raise HTTPException(status_code=404, detail="Rubric not found")

    return JobWithRubric(job=read_job(job), rubric=read_rubric(rubric))
