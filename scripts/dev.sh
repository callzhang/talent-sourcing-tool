#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PYTHON="${BACKEND_PYTHON:-$BACKEND_DIR/.venv/bin/python}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

usage() {
  cat <<EOF
Usage: bash scripts/dev.sh [--help]

Start the local Talent Sourcing Tool backend and frontend.

Prerequisites:
  backend:  cd backend && python -m venv .venv && ./.venv/bin/python -m pip install -e ".[dev]"
  frontend: cd frontend && npm install

Environment overrides:
  BACKEND_PYTHON   Python executable to use. Default: backend/.venv/bin/python
  BACKEND_HOST     Backend bind host. Default: 127.0.0.1
  BACKEND_PORT     Backend port. Default: 8000
  FRONTEND_HOST    Vite bind host. Default: 127.0.0.1
  FRONTEND_PORT    Vite port. Default: 5173

The script initializes the local database, starts both servers, and stops both
processes when interrupted.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  usage >&2
  exit 2
fi

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Missing backend Python at $BACKEND_PYTHON" >&2
  echo 'Run: cd backend && python -m venv .venv && ./.venv/bin/python -m pip install -e ".[dev]"' >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Missing frontend dependencies at $FRONTEND_DIR/node_modules" >&2
  echo "Run: cd frontend && npm install" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

echo "Initializing local database..."
(cd "$BACKEND_DIR" && "$BACKEND_PYTHON" -m app.db.init_db)

echo "Starting backend at http://$BACKEND_HOST:$BACKEND_PORT"
(cd "$BACKEND_DIR" && "$BACKEND_PYTHON" -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT") &
BACKEND_PID=$!

echo "Starting frontend at http://$FRONTEND_HOST:$FRONTEND_PORT"
(cd "$FRONTEND_DIR" && npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    set +e
    wait "$BACKEND_PID"
    STATUS=$?
    exit "$STATUS"
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    set +e
    wait "$FRONTEND_PID"
    STATUS=$?
    exit "$STATUS"
  fi
  sleep 1
done
