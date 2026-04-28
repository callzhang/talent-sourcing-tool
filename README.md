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
