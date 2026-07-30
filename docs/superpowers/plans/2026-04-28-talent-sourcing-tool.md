# Talent Sourcing Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first talent sourcing MVP that manages JDs, searches LinkedIn candidates through a Bright Data adapter, runs Codex-based candidate reviews, records pass/proceed decisions, and turns pass reasons into JD/query refinement suggestions.

**Architecture:** Create a new repo at `/Users/derek/Documents/Projects/talent-sourcing-tool`. The app uses a Python FastAPI backend with focused service modules, a React/Vite frontend, and Turso/libSQL via SQLAlchemy-compatible SQLite for persistence. Codex review is isolated behind a file-protocol worker (`input.json` -> `review.json`) so the backend remains the only database writer.

**Tech Stack:** Python 3.12, FastAPI, SQLModel/SQLAlchemy, pytest, ruff, Vite, React, TypeScript, Vitest, Turso/libSQL-compatible SQLite URL, local `codex exec`.

---

## File Structure

Repository root: `/Users/derek/Documents/Projects/talent-sourcing-tool`

Backend files:

- `backend/pyproject.toml` — backend dependencies and tooling.
- `backend/app/main.py` — FastAPI app factory and router registration.
- `backend/app/core/config.py` — environment settings.
- `backend/app/db/session.py` — database engine/session setup.
- `backend/app/db/models.py` — SQLModel tables.
- `backend/app/db/init_db.py` — schema creation for local development.
- `backend/app/schemas.py` — API request/response schemas.
- `backend/app/services/rubric.py` — natural-language JD to rubric generation, deterministic MVP implementation.
- `backend/app/services/sourcing.py` — Bright Data adapter interface plus mock implementation.
- `backend/app/services/review_worker.py` — Codex file-protocol job runner.
- `backend/app/services/pass_reason.py` — pass-reason draft and refinement suggestion logic.
- `backend/app/api/jobs.py` — JD/rubric endpoints.
- `backend/app/api/search.py` — search run endpoints.
- `backend/app/api/candidates.py` — candidate list/detail endpoints.
- `backend/app/api/reviews.py` — review job and decision endpoints.
- `backend/tests/` — pytest suite.

Frontend files:

- `frontend/package.json` — frontend dependencies and scripts.
- `frontend/src/api.ts` — typed API client.
- `frontend/src/types.ts` — shared TypeScript types.
- `frontend/src/App.tsx` — main shell and route state.
- `frontend/src/pages/JobsPage.tsx` — JD and rubric management.
- `frontend/src/pages/SearchPage.tsx` — search input and search runs.
- `frontend/src/pages/CandidatesPage.tsx` — candidate list.
- `frontend/src/pages/CandidateDetailPage.tsx` — review, feedback, pass/proceed.
- `frontend/src/pages/RefinementsPage.tsx` — query/JD/rubric improvement suggestions.
- `frontend/src/App.test.tsx` — smoke tests.

Docs and scripts:

- `README.md` — local setup and runbook.
- `.gitignore` — Python/Node/env/runtime ignores.
- `scripts/dev.sh` — start backend and frontend.

---

### Task 1: Create Repository Skeleton

**Files:**
- Create: `/Users/derek/Documents/Projects/talent-sourcing-tool/.gitignore`
- Create: `/Users/derek/Documents/Projects/talent-sourcing-tool/README.md`
- Create: `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/pyproject.toml`
- Create: `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/package.json`

- [ ] **Step 1: Create repo directory and initialize git**

Run:

```bash
mkdir -p /Users/derek/Documents/Projects/talent-sourcing-tool
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git init
```

Expected: git initializes an empty repository.

- [ ] **Step 2: Add `.gitignore`**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/.gitignore`:

```gitignore
.env
.env.*
!.env.example
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
dist/
build/
node_modules/
*.db
*.sqlite
*.sqlite3
.codex-review-runs/
review-workspaces/
coverage/
.DS_Store
```

- [ ] **Step 3: Add README**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/README.md`:

```markdown
# Talent Sourcing Tool

Local-first internal tool for JD management, LinkedIn sourcing, Codex-based candidate review, and pass-reason driven sourcing refinement.

## MVP Scope

- Single-user local web app.
- FastAPI backend.
- React/Vite frontend.
- Turso/libSQL-compatible database URL.
- Bright Data adapter boundary.
- Codex review worker using `input.json` and `review.json`.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m app.db.init_db
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.
```

- [ ] **Step 4: Add backend `pyproject.toml`**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/pyproject.toml`:

```toml
[project]
name = "talent-sourcing-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic-settings>=2.6.0",
  "sqlmodel>=0.0.22",
  "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "ruff>=0.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 5: Add frontend `package.json`**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/package.json`:

```json
{
  "name": "talent-sourcing-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0",
    "typescript": "^5.7.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "vitest": "^2.1.0",
    "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 6: Commit skeleton**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add .gitignore README.md backend/pyproject.toml frontend/package.json
git commit -m "chore: initialize talent sourcing tool repo"
```

Expected: commit succeeds.

---

### Task 2: Backend Configuration and Database Models

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/init_db.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_models.py -v
```

Expected: FAIL because `app.db.models` does not exist.

- [ ] **Step 3: Implement config and database session**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./talent_sourcing.sqlite3"
    codex_binary: str = "codex"
    review_workspace_root: str = ".codex-review-runs"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TALENT_")


settings = Settings()
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/db/session.py`:

```python
from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings


engine = create_engine(settings.database_url, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 4: Implement models**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/db/models.py`:

```python
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Job(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("job"), primary_key=True)
    title: str
    description: str
    target_profile_text: str = ""
    red_flags_text: str = ""
    search_notes: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Rubric(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("rubric"), primary_key=True)
    job_id: str = Field(index=True)
    version: int = 1
    rubric_json: str
    source_text_hash: str
    created_at: datetime = Field(default_factory=now_utc)


class SearchRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("search"), primary_key=True)
    job_id: str = Field(index=True)
    query: str
    params_json: str = "{}"
    provider: str = "brightdata"
    status: str = "created"
    error_message: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    completed_at: Optional[datetime] = None


class Candidate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("cand"), primary_key=True)
    linkedin_url: str = Field(unique=True, index=True)
    name: str = ""
    headline: str = ""
    location: str = ""
    current_company: str = ""
    current_title: str = ""
    summary_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SearchResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("result"), primary_key=True)
    search_run_id: str = Field(index=True)
    candidate_id: str = Field(index=True)
    provider: str
    profile_url: str
    normalized_json: str = "{}"
    raw_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)


class CandidateSource(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("source"), primary_key=True)
    candidate_id: str = Field(index=True)
    source_type: str
    url: str
    title: str = ""
    snippet: str = ""
    confidence: float = 0.0
    raw_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)


class ReviewJob(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("reviewjob"), primary_key=True)
    candidate_id: str = Field(index=True)
    job_id: str = Field(index=True)
    rubric_id: str = Field(index=True)
    status: str = "created"
    workspace_path: str = ""
    input_json_path: str = ""
    output_json_path: str = ""
    error_message: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Review(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("review"), primary_key=True)
    review_job_id: str = Field(index=True)
    candidate_id: str = Field(index=True)
    job_id: str = Field(index=True)
    overall_score: float
    recommendation: str
    summary: str
    strengths_json: str = "[]"
    risks_json: str = "[]"
    dimension_scores_json: str = "[]"
    evidence_json: str = "[]"
    suggested_interview_questions_json: str = "[]"
    raw_review_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)


class CandidateDecision(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("decision"), primary_key=True)
    candidate_id: str = Field(index=True)
    job_id: str = Field(index=True)
    decision: str
    decision_note: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class PassReason(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("pass"), primary_key=True)
    candidate_decision_id: str = Field(index=True)
    reason_code: str
    reason_text: str
    agent_suggested: bool = False
    user_edited: bool = False
    evidence_json: str = "[]"
    created_at: datetime = Field(default_factory=now_utc)


class UserFeedback(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("feedback"), primary_key=True)
    candidate_id: str = Field(index=True)
    job_id: str = Field(index=True)
    review_id: str = Field(index=True)
    feedback_text: str
    feedback_type: str
    created_at: datetime = Field(default_factory=now_utc)


class RefinementSuggestion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("refine"), primary_key=True)
    job_id: str = Field(index=True)
    source_scope: str
    suggestion_type: str
    suggestion_text: str
    evidence_json: str = "[]"
    status: str = "new"
    created_at: datetime = Field(default_factory=now_utc)
    resolved_at: Optional[datetime] = None
```

- [ ] **Step 5: Add init script and env example**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/db/init_db.py`:

```python
from sqlmodel import SQLModel

from app.db.models import (  # noqa: F401
    Candidate,
    CandidateDecision,
    CandidateSource,
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
from app.db.session import engine


def main() -> None:
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    main()
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/.env.example`:

```bash
TALENT_DATABASE_URL=sqlite:///./talent_sourcing.sqlite3
TALENT_CODEX_BINARY=codex
TALENT_REVIEW_WORKSPACE_ROOT=.codex-review-runs
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add backend
git commit -m "feat: add backend database models"
```

Expected: commit succeeds.

---

### Task 3: Backend Schemas, Rubric Service, and Job API

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/rubric.py`
- Create: `backend/app/api/jobs.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_jobs_api.py`

- [ ] **Step 1: Write failing API test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_jobs_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_create_job_generates_rubric():
    client = TestClient(app)

    response = client.post(
        "/api/jobs",
        json={
            "title": "AI Product Engineer",
            "description": "Build AI prototypes with strong vibe coding.",
            "target_profile_text": "Strong builder, AI-native, product sense.",
            "red_flags_text": "Only traditional backend, no product sense.",
            "search_notes": "Search early AI app builders.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job"]["title"] == "AI Product Engineer"
    assert data["rubric"]["version"] == 1
    assert len(data["rubric"]["rubric"]["dimensions"]) >= 3
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_jobs_api.py -v
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Add schemas**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/schemas.py`:

```python
from typing import Any

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str
    description: str
    target_profile_text: str = ""
    red_flags_text: str = ""
    search_notes: str = ""


class JobRead(BaseModel):
    id: str
    title: str
    description: str
    target_profile_text: str
    red_flags_text: str
    search_notes: str
    status: str


class RubricRead(BaseModel):
    id: str
    job_id: str
    version: int
    rubric: dict[str, Any]


class JobWithRubric(BaseModel):
    job: JobRead
    rubric: RubricRead


class SearchCreate(BaseModel):
    job_id: str
    query: str
    params: dict[str, Any] = Field(default_factory=dict)


class CandidateRead(BaseModel):
    id: str
    linkedin_url: str
    name: str
    headline: str
    location: str
    current_company: str
    current_title: str


class ReviewStart(BaseModel):
    candidate_id: str
    job_id: str


class DecisionCreate(BaseModel):
    candidate_id: str
    job_id: str
    decision: str
    decision_note: str = ""
    pass_reason_code: str = ""
    pass_reason_text: str = ""
```

- [ ] **Step 4: Add deterministic rubric service**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/services/rubric.py`:

```python
import hashlib
import json

from app.schemas import JobCreate


def source_hash(job: JobCreate) -> str:
    payload = "|".join(
        [job.title, job.description, job.target_profile_text, job.red_flags_text, job.search_notes]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_rubric(job: JobCreate) -> dict:
    text = " ".join(
        [job.title, job.description, job.target_profile_text, job.red_flags_text, job.search_notes]
    ).lower()

    dimensions = [
        {
            "name": "Role Fit",
            "weight": 25,
            "scoring_guidance": "Score evidence that the candidate matches the role's core work.",
        },
        {
            "name": "AI-Native Working Style",
            "weight": 25,
            "scoring_guidance": "Score hands-on use of AI tools, agent workflows, or AI product building.",
        },
        {
            "name": "Builder Evidence",
            "weight": 25,
            "scoring_guidance": "Score public or professional evidence of building prototypes, products, or systems.",
        },
        {
            "name": "Communication and Judgment",
            "weight": 25,
            "scoring_guidance": "Score clarity, product judgment, and ability to work with ambiguous requirements.",
        },
    ]

    if "pmm" in text or "marketing" in text:
        dimensions[1] = {
            "name": "Product Marketing Judgment",
            "weight": 25,
            "scoring_guidance": "Score positioning, messaging, launch, PMF discovery, and user research evidence.",
        }

    return {
        "dimensions": dimensions,
        "positive_signals": [
            "Early-stage startup experience",
            "Public evidence of AI-native work",
            "0-to-1 product or market discovery experience",
        ],
        "negative_signals": [
            "Only large-company execution experience",
            "No evidence of building or shipping",
            "Experience pattern too far from the JD",
        ],
        "red_lines": [job.red_flags_text] if job.red_flags_text else [],
    }


def rubric_to_json(job: JobCreate) -> str:
    return json.dumps(generate_rubric(job), ensure_ascii=False)
```

- [ ] **Step 5: Add jobs API and app**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/api/jobs.py`:

```python
import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import Job, Rubric
from app.db.session import get_session
from app.schemas import JobCreate, JobRead, JobWithRubric, RubricRead
from app.services.rubric import generate_rubric, source_hash

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def read_job(job: Job) -> JobRead:
    return JobRead.model_validate(job.model_dump())


def read_rubric(rubric: Rubric) -> RubricRead:
    return RubricRead(
        id=rubric.id,
        job_id=rubric.job_id,
        version=rubric.version,
        rubric=json.loads(rubric.rubric_json),
    )


@router.post("", response_model=JobWithRubric)
def create_job(payload: JobCreate, session: Session = Depends(get_session)) -> JobWithRubric:
    job = Job(**payload.model_dump())
    session.add(job)
    session.commit()
    session.refresh(job)

    rubric = Rubric(
        job_id=job.id,
        version=1,
        rubric_json=json.dumps(generate_rubric(payload), ensure_ascii=False),
        source_text_hash=source_hash(payload),
    )
    session.add(rubric)
    session.commit()
    session.refresh(rubric)

    return JobWithRubric(job=read_job(job), rubric=read_rubric(rubric))


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)) -> list[JobRead]:
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return [read_job(job) for job in jobs]
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.api import jobs
from app.db.session import engine

app = FastAPI(title="Talent Sourcing Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(engine)

app.include_router(jobs.router)
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/api/__init__.py`:

```python
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_jobs_api.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add backend
git commit -m "feat: add job and rubric API"
```

Expected: commit succeeds.

---

### Task 4: Sourcing Connector and Candidate Import API

**Files:**
- Create: `backend/app/services/sourcing.py`
- Create: `backend/app/api/search.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_search_api.py`

- [ ] **Step 1: Write failing search API test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_search_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_search_upserts_candidates_by_linkedin_url():
    client = TestClient(app)
    job_response = client.post(
        "/api/jobs",
        json={"title": "Founding PMM", "description": "Find PMF wedge"},
    )
    job_id = job_response.json()["job"]["id"]

    response = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "founding PMM AI startup", "params": {"limit": 2}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["candidates"]) == 2
    assert data["candidates"][0]["linkedin_url"].startswith("https://www.linkedin.com/in/")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_search_api.py -v
```

Expected: FAIL because `/api/search` is not registered.

- [ ] **Step 3: Implement sourcing service**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/services/sourcing.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateSourceResult:
    linkedin_url: str
    name: str
    headline: str = ""
    location: str = ""
    current_company: str = ""
    current_title: str = ""
    raw: dict | None = None


class SourcingConnector:
    def search_people(self, query: str, params: dict) -> list[CandidateSourceResult]:
        raise NotImplementedError


class MockBrightDataConnector(SourcingConnector):
    def search_people(self, query: str, params: dict) -> list[CandidateSourceResult]:
        limit = int(params.get("limit", 2))
        fixtures = [
            CandidateSourceResult(
                linkedin_url="https://www.linkedin.com/in/alex-ai-builder",
                name="Alex Builder",
                headline="Founding AI Product Engineer",
                location="San Francisco Bay Area",
                current_company="Early AI Startup",
                current_title="Founding Engineer",
                raw={"query": query},
            ),
            CandidateSourceResult(
                linkedin_url="https://www.linkedin.com/in/jordan-pmf",
                name="Jordan PMF",
                headline="Founding PMM, AI workflows",
                location="New York, NY",
                current_company="Workflow AI Co",
                current_title="Founding PMM",
                raw={"query": query},
            ),
        ]
        return fixtures[:limit]


def get_sourcing_connector() -> SourcingConnector:
    return MockBrightDataConnector()
```

- [ ] **Step 4: Implement search API**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/api/search.py`:

```python
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import Candidate, SearchResult, SearchRun
from app.db.session import get_session
from app.schemas import CandidateRead, SearchCreate
from app.services.sourcing import get_sourcing_connector

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("")
def create_search(payload: SearchCreate, session: Session = Depends(get_session)) -> dict:
    run = SearchRun(
        job_id=payload.job_id,
        query=payload.query,
        params_json=json.dumps(payload.params),
        provider="brightdata",
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    connector = get_sourcing_connector()
    results = connector.search_people(payload.query, payload.params)
    candidates: list[CandidateRead] = []

    for result in results:
        candidate = session.exec(
            select(Candidate).where(Candidate.linkedin_url == result.linkedin_url)
        ).first()
        if candidate is None:
            candidate = Candidate(
                linkedin_url=result.linkedin_url,
                name=result.name,
                headline=result.headline,
                location=result.location,
                current_company=result.current_company,
                current_title=result.current_title,
            )
            session.add(candidate)
            session.commit()
            session.refresh(candidate)

        session.add(
            SearchResult(
                search_run_id=run.id,
                candidate_id=candidate.id,
                provider="brightdata",
                profile_url=result.linkedin_url,
                normalized_json=json.dumps(result.__dict__, default=str),
                raw_json=json.dumps(result.raw or {}),
            )
        )
        candidates.append(CandidateRead.model_validate(candidate.model_dump()))

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()

    return {"id": run.id, "status": run.status, "candidates": candidates}
```

- [ ] **Step 5: Register router**

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.api import jobs, search
from app.db.session import engine

app = FastAPI(title="Talent Sourcing Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(engine)

app.include_router(jobs.router)
app.include_router(search.router)
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_search_api.py tests/test_jobs_api.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add backend
git commit -m "feat: add candidate sourcing API"
```

Expected: commit succeeds.

---

### Task 5: Review Worker and Review API

**Files:**
- Create: `backend/app/services/review_worker.py`
- Create: `backend/app/api/reviews.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_review_worker.py`
- Create: `backend/tests/test_reviews_api.py`

- [ ] **Step 1: Write failing review worker test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_review_worker.py`:

```python
import json
from pathlib import Path

from app.services.review_worker import ReviewWorker


def test_review_worker_reads_review_json_from_fake_codex(tmp_path: Path):
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        """
import json
import pathlib
import sys

workspace = pathlib.Path(sys.argv[-1])
(workspace / "review.json").write_text(json.dumps({
  "candidate_id": "cand_1",
  "job_id": "job_1",
  "overall_score": 82,
  "recommendation": "proceed",
  "decision_summary": "Strong builder evidence.",
  "dimension_scores": [],
  "strengths": ["Builder"],
  "risks": [],
  "evidence": [],
  "sources": [],
  "suggested_interview_questions": [],
  "uncertainties": [],
  "review_notes": "Generated by fake codex"
}))
""".strip()
    )

    worker = ReviewWorker(codex_command=["python", str(fake_codex)], workspace_root=tmp_path)
    result = worker.run_review(
        review_job_id="reviewjob_1",
        payload={"candidate": {"id": "cand_1"}, "job": {"id": "job_1"}},
    )

    assert result.review["overall_score"] == 82
    assert result.review["recommendation"] == "proceed"
    assert json.loads(result.input_path.read_text())["review_job_id"] == "reviewjob_1"
```

- [ ] **Step 2: Run worker test and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_review_worker.py -v
```

Expected: FAIL because review worker does not exist.

- [ ] **Step 3: Implement review worker**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/services/review_worker.py`:

```python
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReviewWorkerResult:
    workspace: Path
    input_path: Path
    output_path: Path
    review: dict[str, Any]


class ReviewWorker:
    def __init__(self, codex_command: list[str], workspace_root: str | Path):
        self.codex_command = codex_command
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def run_review(self, review_job_id: str, payload: dict[str, Any]) -> ReviewWorkerResult:
        workspace = Path(tempfile.mkdtemp(prefix=f"{review_job_id}_", dir=self.workspace_root))
        temp_home = workspace / "home"
        temp_home.mkdir()

        input_path = workspace / "input.json"
        output_path = workspace / "review.json"
        schema_path = workspace / "review.schema.json"

        full_payload = {
            "review_job_id": review_job_id,
            **payload,
            "output_schema_path": str(schema_path),
        }
        input_path.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2))
        schema_path.write_text(json.dumps({"type": "object"}, indent=2))

        env = os.environ.copy()
        env["HOME"] = str(temp_home)

        command = [*self.codex_command, str(workspace)]
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=env,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"codex review failed: {completed.stderr.strip() or completed.stdout.strip()}"
            )
        if not output_path.exists():
            raise RuntimeError("codex review did not create review.json")

        review = json.loads(output_path.read_text())
        required = {"candidate_id", "job_id", "overall_score", "recommendation", "decision_summary"}
        missing = required - set(review)
        if missing:
            raise ValueError(f"review.json missing required fields: {sorted(missing)}")

        return ReviewWorkerResult(
            workspace=workspace,
            input_path=input_path,
            output_path=output_path,
            review=review,
        )
```

- [ ] **Step 4: Run worker test**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_review_worker.py -v
```

Expected: PASS.

- [ ] **Step 5: Write failing review API test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_reviews_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_pass_requires_pass_reason():
    client = TestClient(app)
    job = client.post("/api/jobs", json={"title": "AI Product Engineer", "description": "Build"}).json()
    job_id = job["job"]["id"]
    search = client.post(
        "/api/search",
        json={"job_id": job_id, "query": "ai product engineer", "params": {"limit": 1}},
    ).json()
    candidate_id = search["candidates"][0]["id"]

    response = client.post(
        "/api/reviews/decision",
        json={"candidate_id": candidate_id, "job_id": job_id, "decision": "pass"},
    )

    assert response.status_code == 400
    assert "pass reason" in response.json()["detail"].lower()
```

- [ ] **Step 6: Run API test and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_reviews_api.py -v
```

Expected: FAIL because reviews API does not exist.

- [ ] **Step 7: Implement review API with decision validation**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/api/reviews.py`:

```python
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import (
    Candidate,
    CandidateDecision,
    Job,
    PassReason,
    Review,
    ReviewJob,
    Rubric,
)
from app.db.session import get_session
from app.schemas import DecisionCreate, ReviewStart
from app.services.review_worker import ReviewWorker

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/start")
def start_review(payload: ReviewStart, session: Session = Depends(get_session)) -> dict:
    candidate = session.get(Candidate, payload.candidate_id)
    job = session.get(Job, payload.job_id)
    if candidate is None or job is None:
        raise HTTPException(status_code=404, detail="candidate or job not found")

    rubric = session.exec(
        select(Rubric).where(Rubric.job_id == job.id).order_by(Rubric.version.desc())
    ).first()
    if rubric is None:
        raise HTTPException(status_code=400, detail="job has no rubric")

    review_job = ReviewJob(candidate_id=candidate.id, job_id=job.id, rubric_id=rubric.id)
    session.add(review_job)
    session.commit()
    session.refresh(review_job)

    worker = ReviewWorker(
        codex_command=[settings.codex_binary, "exec"],
        workspace_root=settings.review_workspace_root,
    )
    try:
        result = worker.run_review(
            review_job_id=review_job.id,
            payload={
                "candidate": candidate.model_dump(),
                "job": job.model_dump(),
                "rubric": json.loads(rubric.rubric_json),
                "allowed_tasks": [
                    "visit_linkedin_profile",
                    "search_public_web",
                    "find_github",
                    "find_x_or_blog",
                    "score_against_rubric",
                    "write_review_json",
                ],
            },
        )
    except Exception as exc:
        review_job.status = "failed"
        review_job.error_message = str(exc)
        session.add(review_job)
        session.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    review_job.status = "completed"
    review_job.workspace_path = str(result.workspace)
    review_job.input_json_path = str(result.input_path)
    review_job.output_json_path = str(result.output_path)
    session.add(review_job)

    review = Review(
        review_job_id=review_job.id,
        candidate_id=candidate.id,
        job_id=job.id,
        overall_score=float(result.review["overall_score"]),
        recommendation=str(result.review["recommendation"]),
        summary=str(result.review["decision_summary"]),
        strengths_json=json.dumps(result.review.get("strengths", [])),
        risks_json=json.dumps(result.review.get("risks", [])),
        dimension_scores_json=json.dumps(result.review.get("dimension_scores", [])),
        evidence_json=json.dumps(result.review.get("evidence", [])),
        suggested_interview_questions_json=json.dumps(
            result.review.get("suggested_interview_questions", [])
        ),
        raw_review_json=json.dumps(result.review),
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return {"review_job_id": review_job.id, "review_id": review.id, "review": result.review}


@router.post("/decision")
def create_decision(payload: DecisionCreate, session: Session = Depends(get_session)) -> dict:
    if payload.decision not in {"pass", "proceed"}:
        raise HTTPException(status_code=400, detail="decision must be pass or proceed")
    if payload.decision == "pass" and not payload.pass_reason_text.strip():
        raise HTTPException(status_code=400, detail="pass reason is required for pass decision")

    decision = CandidateDecision(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        decision=payload.decision,
        decision_note=payload.decision_note,
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)

    pass_reason = None
    if payload.decision == "pass":
        pass_reason = PassReason(
            candidate_decision_id=decision.id,
            reason_code=payload.pass_reason_code or "user_specified",
            reason_text=payload.pass_reason_text,
            agent_suggested=False,
            user_edited=True,
        )
        session.add(pass_reason)
        session.commit()
        session.refresh(pass_reason)

    return {
        "decision": decision.model_dump(),
        "pass_reason": pass_reason.model_dump() if pass_reason else None,
    }
```

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.api import jobs, reviews, search
from app.db.session import engine

app = FastAPI(title="Talent Sourcing Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(engine)

app.include_router(jobs.router)
app.include_router(search.router)
app.include_router(reviews.router)
```

- [ ] **Step 8: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_review_worker.py tests/test_reviews_api.py tests/test_search_api.py tests/test_jobs_api.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add backend
git commit -m "feat: add codex review worker and decisions"
```

Expected: commit succeeds.

---

### Task 6: Pass Reason Drafting and Refinement Suggestions

**Files:**
- Create: `backend/app/services/pass_reason.py`
- Modify: `backend/app/api/reviews.py`
- Create: `backend/tests/test_pass_reason.py`

- [ ] **Step 1: Write failing pass reason test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/tests/test_pass_reason.py`:

```python
from app.services.pass_reason import draft_pass_reason, suggest_refinements


def test_draft_pass_reason_prioritizes_weak_builder_evidence():
    review = {
        "risks": ["No public evidence of shipping AI products"],
        "dimension_scores": [{"name": "Builder Evidence", "score": 35}],
    }
    draft = draft_pass_reason(review)

    assert draft["reason_code"] == "weak_builder_evidence"
    assert "builder" in draft["reason_text"].lower()


def test_suggest_refinements_mentions_search_query():
    suggestions = suggest_refinements(
        pass_reasons=[
            {"reason_code": "too_enterprise_sales_oriented", "reason_text": "Too sales-heavy"}
        ]
    )

    assert any(item["suggestion_type"] == "query_rewrite" for item in suggestions)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_pass_reason.py -v
```

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement pass reason service**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/services/pass_reason.py`:

```python
from collections import Counter
from typing import Any


def draft_pass_reason(review: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            " ".join(str(item) for item in review.get("risks", [])),
            " ".join(str(item) for item in review.get("uncertainties", [])),
            str(review.get("decision_summary", "")),
        ]
    ).lower()

    if "builder" in text or "shipping" in text or "prototype" in text:
        return {
            "reason_code": "weak_builder_evidence",
            "reason_text": "Candidate does not show enough public or professional evidence of building and shipping AI product prototypes.",
            "evidence": review.get("risks", []),
        }
    if "enterprise sales" in text or "sales-heavy" in text:
        return {
            "reason_code": "too_enterprise_sales_oriented",
            "reason_text": "Candidate appears too oriented toward traditional enterprise sales rather than PMF discovery or AI product building.",
            "evidence": review.get("risks", []),
        }
    if "ai-native" in text or "ai native" in text:
        return {
            "reason_code": "insufficient_ai_native_signal",
            "reason_text": "Candidate does not show enough evidence of AI-native work habits or AI workflow depth.",
            "evidence": review.get("risks", []),
        }
    return {
        "reason_code": "insufficient_public_evidence",
        "reason_text": "Available evidence is not strong enough to justify proceeding.",
        "evidence": review.get("risks", []),
    }


def suggest_refinements(pass_reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(reason["reason_code"] for reason in pass_reasons)
    suggestions: list[dict[str, Any]] = []

    if counts["too_enterprise_sales_oriented"]:
        suggestions.append(
            {
                "suggestion_type": "query_rewrite",
                "suggestion_text": "Reduce traditional enterprise sales false positives by adding terms like 'founding PMM', 'PMF', 'AI workflow', and excluding 'account executive' or pure sales titles.",
                "evidence": [reason for reason in pass_reasons if reason["reason_code"] == "too_enterprise_sales_oriented"],
            }
        )
    if counts["weak_builder_evidence"]:
        suggestions.append(
            {
                "suggestion_type": "rubric_adjustment",
                "suggestion_text": "Increase weight for public builder evidence such as GitHub, shipped demos, prototypes, open-source projects, or product launches.",
                "evidence": [reason for reason in pass_reasons if reason["reason_code"] == "weak_builder_evidence"],
            }
        )
    if not suggestions:
        suggestions.append(
            {
                "suggestion_type": "jd_rewrite",
                "suggestion_text": "Clarify must-have evidence in the JD so the next sourcing batch has sharper screening criteria.",
                "evidence": pass_reasons,
            }
        )
    return suggestions
```

- [ ] **Step 4: Add draft endpoint**

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/backend/app/api/reviews.py` by adding this import:

```python
from app.services.pass_reason import draft_pass_reason
```

Add this route before `create_decision`:

```python
@router.get("/{review_id}/draft-pass-reason")
def draft_review_pass_reason(review_id: str, session: Session = Depends(get_session)) -> dict:
    review = session.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    raw = json.loads(review.raw_review_json)
    return draft_pass_reason(raw)
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest tests/test_pass_reason.py tests/test_reviews_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add backend
git commit -m "feat: add pass reason drafting"
```

Expected: commit succeeds.

---

### Task 7: Frontend Shell and API Client

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: Create frontend config**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Talent Sourcing Tool</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: []
  }
});
```

- [ ] **Step 2: Add types and API client**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/types.ts`:

```ts
export type Job = {
  id: string;
  title: string;
  description: string;
  target_profile_text: string;
  red_flags_text: string;
  search_notes: string;
  status: string;
};

export type Rubric = {
  id: string;
  job_id: string;
  version: number;
  rubric: {
    dimensions: Array<{ name: string; weight: number; scoring_guidance: string }>;
    positive_signals: string[];
    negative_signals: string[];
    red_lines: string[];
  };
};

export type Candidate = {
  id: string;
  linkedin_url: string;
  name: string;
  headline: string;
  location: string;
  current_company: string;
  current_title: string;
};
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/api.ts`:

```ts
import type { Candidate, Job, Rubric } from "./types";

const API_BASE = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }
  return response.json() as Promise<T>;
}

export const api = {
  createJob(payload: {
    title: string;
    description: string;
    target_profile_text: string;
    red_flags_text: string;
    search_notes: string;
  }) {
    return request<{ job: Job; rubric: Rubric }>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  listJobs() {
    return request<Job[]>("/api/jobs");
  },
  search(payload: { job_id: string; query: string; params: Record<string, unknown> }) {
    return request<{ id: string; status: string; candidates: Candidate[] }>("/api/search", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  decide(payload: {
    candidate_id: string;
    job_id: string;
    decision: "pass" | "proceed";
    decision_note?: string;
    pass_reason_code?: string;
    pass_reason_text?: string;
  }) {
    return request<{ decision: unknown; pass_reason: unknown }>("/api/reviews/decision", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }
};
```

- [ ] **Step 3: Add app shell**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/App.tsx`:

```tsx
import { useState } from "react";

type Page = "jobs" | "search" | "candidates" | "refinements";

export function App() {
  const [page, setPage] = useState<Page>("jobs");

  return (
    <main style={{ fontFamily: "ui-sans-serif", padding: 24, maxWidth: 1120, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>Talent Sourcing Tool</h1>
          <p>JD → LinkedIn sourcing → AI review → pass/proceed feedback loop.</p>
        </div>
        <nav style={{ display: "flex", gap: 8 }}>
          {(["jobs", "search", "candidates", "refinements"] as Page[]).map((item) => (
            <button key={item} onClick={() => setPage(item)} aria-pressed={page === item}>
              {item}
            </button>
          ))}
        </nav>
      </header>
      <section style={{ marginTop: 32 }}>
        {page === "jobs" && <h2>JD Management</h2>}
        {page === "search" && <h2>Search Runs</h2>}
        {page === "candidates" && <h2>Candidates</h2>}
        {page === "refinements" && <h2>Refinement Suggestions</h2>}
      </section>
    </main>
  );
}
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/main.tsx`:

```tsx
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(<App />);
```

- [ ] **Step 4: Add smoke test**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { App } from "./App";

it("renders the app shell", () => {
  render(<App />);
  expect(screen.getByText("Talent Sourcing Tool")).toBeInTheDocument();
  expect(screen.getByText("JD Management")).toBeInTheDocument();
});
```

- [ ] **Step 5: Run frontend tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/frontend
npm install
npm test
npm run lint
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add frontend
git commit -m "feat: add frontend app shell"
```

Expected: commit succeeds.

---

### Task 8: Frontend MVP Workflow Pages

**Files:**
- Create: `frontend/src/pages/JobsPage.tsx`
- Create: `frontend/src/pages/SearchPage.tsx`
- Create: `frontend/src/pages/CandidatesPage.tsx`
- Create: `frontend/src/pages/RefinementsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add Jobs page**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/pages/JobsPage.tsx`:

```tsx
import { FormEvent, useState } from "react";
import { api } from "../api";
import type { Job, Rubric } from "../types";

export function JobsPage() {
  const [job, setJob] = useState<Job | null>(null);
  const [rubric, setRubric] = useState<Rubric | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api.createJob({
      title: String(form.get("title") ?? ""),
      description: String(form.get("description") ?? ""),
      target_profile_text: String(form.get("target_profile_text") ?? ""),
      red_flags_text: String(form.get("red_flags_text") ?? ""),
      search_notes: String(form.get("search_notes") ?? "")
    });
    setJob(result.job);
    setRubric(result.rubric);
  }

  return (
    <section>
      <h2>JD Management</h2>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <input name="title" placeholder="Job title" required />
        <textarea name="description" placeholder="JD description" required rows={4} />
        <textarea name="target_profile_text" placeholder="Target profile" rows={3} />
        <textarea name="red_flags_text" placeholder="Red flags" rows={3} />
        <textarea name="search_notes" placeholder="Search notes" rows={3} />
        <button type="submit">Create JD and Rubric</button>
      </form>
      {job && <p>Created: {job.title}</p>}
      {rubric && (
        <div>
          <h3>Rubric</h3>
          <ul>
            {rubric.rubric.dimensions.map((dimension) => (
              <li key={dimension.name}>
                {dimension.name}: {dimension.weight}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Add Search page**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/pages/SearchPage.tsx`:

```tsx
import { FormEvent, useState } from "react";
import { api } from "../api";
import type { Candidate } from "../types";

export function SearchPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api.search({
      job_id: String(form.get("job_id") ?? ""),
      query: String(form.get("query") ?? ""),
      params: { limit: Number(form.get("limit") ?? 2) }
    });
    setCandidates(result.candidates);
  }

  return (
    <section>
      <h2>Search Runs</h2>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <input name="job_id" placeholder="Job ID" required />
        <input name="query" placeholder="LinkedIn search query" required />
        <input name="limit" placeholder="Limit" type="number" defaultValue={2} min={1} />
        <button type="submit">Search</button>
      </form>
      <ul>
        {candidates.map((candidate) => (
          <li key={candidate.id}>
            <a href={candidate.linkedin_url}>{candidate.name}</a> — {candidate.headline}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 3: Add Candidates and Refinements pages**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/pages/CandidatesPage.tsx`:

```tsx
export function CandidatesPage() {
  return (
    <section>
      <h2>Candidates</h2>
      <p>Candidate detail and review display will use the backend review records after review jobs run.</p>
    </section>
  );
}
```

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/pages/RefinementsPage.tsx`:

```tsx
export function RefinementsPage() {
  return (
    <section>
      <h2>Refinement Suggestions</h2>
      <p>Pass reasons will feed JD, rubric, and query improvements here.</p>
    </section>
  );
}
```

- [ ] **Step 4: Wire pages into App**

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/App.tsx`:

```tsx
import { useState } from "react";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobsPage } from "./pages/JobsPage";
import { RefinementsPage } from "./pages/RefinementsPage";
import { SearchPage } from "./pages/SearchPage";

type Page = "jobs" | "search" | "candidates" | "refinements";

export function App() {
  const [page, setPage] = useState<Page>("jobs");

  return (
    <main style={{ fontFamily: "ui-sans-serif", padding: 24, maxWidth: 1120, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>Talent Sourcing Tool</h1>
          <p>JD → LinkedIn sourcing → AI review → pass/proceed feedback loop.</p>
        </div>
        <nav style={{ display: "flex", gap: 8 }}>
          {(["jobs", "search", "candidates", "refinements"] as Page[]).map((item) => (
            <button key={item} onClick={() => setPage(item)} aria-pressed={page === item}>
              {item}
            </button>
          ))}
        </nav>
      </header>
      <section style={{ marginTop: 32 }}>
        {page === "jobs" && <JobsPage />}
        {page === "search" && <SearchPage />}
        {page === "candidates" && <CandidatesPage />}
        {page === "refinements" && <RefinementsPage />}
      </section>
    </main>
  );
}
```

- [ ] **Step 5: Update smoke test**

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { App } from "./App";

it("renders the app shell and JD form", () => {
  render(<App />);
  expect(screen.getByText("Talent Sourcing Tool")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Job title")).toBeInTheDocument();
});
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/frontend
npm test
npm run lint
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add frontend
git commit -m "feat: add frontend MVP pages"
```

Expected: commit succeeds.

---

### Task 9: Developer Run Script and Final Verification

**Files:**
- Create: `scripts/dev.sh`
- Modify: `README.md`

- [ ] **Step 1: Add dev script**

Create `/Users/derek/Documents/Projects/talent-sourcing-tool/scripts/dev.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting backend on http://localhost:8000"
(
  cd "$ROOT/backend"
  source .venv/bin/activate
  python -m app.db.init_db
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173"
(
  cd "$ROOT/frontend"
  npm run dev
) &
FRONTEND_PID=$!

trap 'kill "$BACKEND_PID" "$FRONTEND_PID"' EXIT
wait
```

Run:

```bash
chmod +x /Users/derek/Documents/Projects/talent-sourcing-tool/scripts/dev.sh
```

- [ ] **Step 2: Update README with MVP caveats**

Modify `/Users/derek/Documents/Projects/talent-sourcing-tool/README.md` by appending:

```markdown
## Current MVP Caveats

- Bright Data integration is represented by a connector boundary and mock connector until real MCP/API credentials are configured.
- Codex review worker is implemented as a file protocol. Real LinkedIn browser access depends on local Codex/browser-use availability and logged-in browser state.
- V1 is single-user and local-first.
- `pass` decisions require a pass reason so the tool can improve JD, rubric, and query quality over time.

## Run Both Services

```bash
./scripts/dev.sh
```
```

- [ ] **Step 3: Run all backend tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/backend
source .venv/bin/activate
pytest -v
ruff check .
```

Expected: PASS.

- [ ] **Step 4: Run all frontend tests**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool/frontend
npm test
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
cd /Users/derek/Documents/Projects/talent-sourcing-tool
git add README.md scripts/dev.sh
git commit -m "chore: add development runbook"
```

Expected: commit succeeds.

---

## Plan Self-Review

Spec coverage:

- JD management: Task 3 and Task 8.
- Rubric generation: Task 3.
- Bright Data connector boundary: Task 4.
- Candidate deduplication by LinkedIn URL: Task 2 and Task 4.
- Codex file-protocol review worker: Task 5.
- Pass/proceed decision: Task 5.
- Required pass reason: Task 5.
- Pass reason agent/refinement loop foundation: Task 6.
- Local FastAPI + React/Vite + Turso-compatible database: Tasks 1-9.
- New repo under `/Users/derek/Documents/Projects/`: Task 1.

Known intentional simplifications:

- Bright Data is mocked behind an adapter until real API/MCP details are supplied.
- Rubric generation is deterministic in MVP plan; it establishes the interface before LLM/provider wiring.
- Frontend review detail is skeletal after Task 8; backend review workflow is implemented first.
- Full Vercel deployment and full ATS pipeline remain out of scope.
