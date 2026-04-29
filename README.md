# Talent Sourcing Tool

Local-first MVP for JD management, multi-channel candidate sourcing, Codex-based candidate review, and pass-reason-driven sourcing refinement.

This repository is intentionally local-first. It does not include auth, deployment, outreach automation, or multi-user workflow support.

## Architecture

- `backend/` is a FastAPI API that owns all persistent writes.
- `frontend/` is a React/Vite UI that talks to the backend at `http://localhost:8000` by default.
- Candidate sourcing runs through a live channel router. Public channels use direct HTTP APIs, and private channels use configured provider credentials.
- Candidate review is behind a local Codex file-protocol worker. The backend writes `input.json`, runs the configured Codex command in an isolated workspace with a temporary `HOME`, validates `review.json`, then stores the result.
- Persistence uses a SQLModel/SQLAlchemy database URL. The default is local SQLite, and the schema is intended to remain Turso/libSQL-compatible for the MVP.

## Requirements

- Python 3.12
- Node.js 20 or newer
- npm
- Local `codex` CLI if you want to run real review jobs

## Environment

Backend settings use the `TALENT_` prefix and can be defined in `backend/.env`. The backend also reads the repository root `.env`, which is useful when frontend and backend share sourcing credentials locally.

```bash
cd backend
cp .env.example .env
```

Available settings:

- `TALENT_DATABASE_URL`: SQLAlchemy-compatible database URL. Defaults to `sqlite:///./talent_sourcing.sqlite3` in `backend/`.
- `TALENT_CODEX_BINARY`: Codex executable used by the review worker. Defaults to `codex`.
- `TALENT_REVIEW_WORKSPACE_ROOT`: local directory for generated review workspaces. Defaults to `.codex-review-runs`.
- `TALENT_SOURCING_PROVIDER`: sourcing execution mode. The current supported value is `live`.
- `TALENT_EXA_API_KEY`: required for the `exa` channel and for `linkedin` when Exa is the retrieval backend.
- `TALENT_BRIGHTDATA_API_KEY`: required for `brightdata_discover` and for `linkedin` when Bright Data SERP is the retrieval backend.
- `TALENT_BRIGHTDATA_ZONE`: Bright Data SERP zone name required together with `TALENT_BRIGHTDATA_API_KEY`.

Frontend settings can be defined in `frontend/.env.local`.

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Backend Setup

```bash
cd backend
python -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/python -m app.db.init_db
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. FastAPI docs are available at `http://localhost:8000/docs`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## One-Command Local Development

After installing backend and frontend dependencies, run both servers from the repository root:

```bash
bash scripts/dev.sh
```

The script initializes the local database, starts the backend on port `8000`, starts Vite on port `5173`, and stops both processes when interrupted.

For options:

```bash
bash scripts/dev.sh --help
```

## Sourcing Channels

The app calls `get_sourcing_connector()` in `backend/app/services/sourcing.py`. The current implementation is live-only and routes each selected search channel separately:

- `github`: GitHub user search API plus per-user profile lookup
- `openreview`: OpenReview notes search API
- `arxiv`: arXiv Atom API
- `exa`: Exa Search API
- `linkedin`: Exa domain search or Bright Data SERP, depending on which credential is configured
- `brightdata_discover`: Bright Data SERP API

Candidate identity is now a generic `profile_url` plus `profile_source`, not a LinkedIn-only URL. Provider-specific response details remain under each candidate's `profile_data.raw` payload.

## Codex Review Worker

Review jobs are started through the backend. The worker:

- creates a temporary review workspace under `TALENT_REVIEW_WORKSPACE_ROOT`;
- creates temporary `HOME` and `CODEX_HOME` directories for the Codex process;
- writes `input.json` and `review.schema.json`;
- runs `TALENT_CODEX_BINARY exec` from the review workspace with a prompt that instructs Codex to read `input.json`, follow `review.schema.json`, and write `review.json`;
- when the configured command is `codex exec`, copies only `auth.json` into the temporary `CODEX_HOME` so the process can authenticate without loading unrelated local Codex config;
- when the configured command is `codex exec`, adds `--cd <workspace>`, `--sandbox workspace-write`, `--skip-git-repo-check`, `--ephemeral`, `--ignore-user-config`, and `--ignore-rules` to avoid loading unrelated local Codex config or project rules;
- requires the worker to create `review.json`;
- validates required review fields before persisting the review.

The Codex process is file-boundary-only from the backend perspective. It should not write directly to the database. The backend preserves the parent process environment for executable lookup and credentials, but isolates Codex state/config with temporary `HOME` and `CODEX_HOME` plus the Codex exec flags above. Generated review workspaces are ignored by git.

## Database Note

Local development defaults to SQLite at `backend/talent_sourcing.sqlite3`. App startup creates missing tables and applies the current lightweight SQLite schema migration for existing local databases. Keep migrations and schema choices compatible with Turso/libSQL-style SQLite semantics: avoid database-specific features that would not work in libSQL, and use SQLModel/SQLAlchemy-compatible URLs through `TALENT_DATABASE_URL`.

## Testing

Run backend verification:

```bash
cd backend
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check app tests
```

Run frontend verification:

```bash
cd frontend
npm run test
npm run build
npm run lint
```

Run the development script help check without starting servers:

```bash
bash scripts/dev.sh --help
```

## Limitations

- Single-user local MVP only.
- No authentication, authorization, or deployment setup.
- No ATS pipeline beyond `pass` and `proceed`.
- No automated outreach or email/calendar integration.
- LinkedIn search requires either Exa or Bright Data SERP credentials; there is no unauthenticated LinkedIn search path.
- `brightdata_discover` requires both a Bright Data API key and a SERP zone.
- Codex review quality depends on the local Codex CLI, local session capabilities, and the evidence available to the worker.
