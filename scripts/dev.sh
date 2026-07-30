#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
DEFAULT_BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
BACKEND_PYTHON="${BACKEND_PYTHON:-$DEFAULT_BACKEND_PYTHON}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_RELOAD="${BACKEND_RELOAD:-1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_SERVER_MODE="${FRONTEND_SERVER_MODE:-dev}"

usage() {
  cat <<EOF
Usage: bash scripts/dev.sh [--help]

Start the local Talent Sourcing Tool backend and frontend.

Prerequisites:
  backend:  Python 3.12+; default backend/.venv will be auto-created if missing
  frontend: frontend/node_modules will be auto-installed if missing

Environment overrides:
  BACKEND_PYTHON   Python executable to use. Default: backend/.venv/bin/python
  BACKEND_HOST     Backend bind host. Default: 127.0.0.1
  BACKEND_PORT     Backend port. Default: 8000
  BACKEND_RELOAD   Set to 0 to disable uvicorn reload. Default: 1
  FRONTEND_HOST    Vite bind host. Default: 127.0.0.1
  FRONTEND_PORT    Vite port. Default: 5173
  FRONTEND_SERVER_MODE  dev or preview. Default: dev

The script initializes the local database, starts both servers, and stops both
processes when interrupted.

If BACKEND_PYTHON points to a custom interpreter, it must already have the
backend dependencies installed.
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

choose_bootstrap_python() {
  local candidate
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

require_python_312() {
  local python_bin="$1"
  if ! "$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    echo "Python 3.12+ is required, but $python_bin is incompatible." >&2
    exit 1
  fi
}

backend_import_probe() {
  local python_bin="$1"
  (cd "$BACKEND_DIR" && "$python_bin" -c "import fastapi, uvicorn, pydantic_settings, sqlmodel, httpx" >/dev/null 2>&1)
}

ensure_backend_python() {
  if [[ "$BACKEND_PYTHON" != "$DEFAULT_BACKEND_PYTHON" ]]; then
    if [[ ! -x "$BACKEND_PYTHON" ]]; then
      echo "Missing backend Python at $BACKEND_PYTHON" >&2
      exit 1
    fi
    require_python_312 "$BACKEND_PYTHON"
    if ! backend_import_probe "$BACKEND_PYTHON"; then
      echo "Custom BACKEND_PYTHON is missing backend dependencies: $BACKEND_PYTHON" >&2
      echo 'Run: cd backend && '"$BACKEND_PYTHON"' -m pip install -e ".[dev]"' >&2
      exit 1
    fi
    return 0
  fi

  if [[ ! -x "$BACKEND_PYTHON" ]]; then
    local bootstrap_python
    bootstrap_python="$(choose_bootstrap_python)" || {
      echo "Missing Python 3.12+ to create backend virtualenv at $BACKEND_PYTHON" >&2
      exit 1
    }
    require_python_312 "$bootstrap_python"
    echo "Bootstrapping backend virtualenv with $bootstrap_python..."
    (cd "$BACKEND_DIR" && "$bootstrap_python" -m venv .venv)
  fi

  require_python_312 "$BACKEND_PYTHON"

  if ! backend_import_probe "$BACKEND_PYTHON"; then
    echo 'Installing backend dependencies into backend/.venv...'
    (cd "$BACKEND_DIR" && "$BACKEND_PYTHON" -m pip install -e ".[dev]")
  fi
}

ensure_backend_python

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm ci)
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
BACKEND_ARGS=( -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" )
if [[ "$BACKEND_RELOAD" == "1" ]]; then
  BACKEND_ARGS+=( --reload )
fi
(cd "$BACKEND_DIR" && "$BACKEND_PYTHON" "${BACKEND_ARGS[@]}") &
BACKEND_PID=$!

echo "Starting frontend at http://$FRONTEND_HOST:$FRONTEND_PORT"
if [[ "$FRONTEND_SERVER_MODE" == "preview" ]]; then
  (cd "$FRONTEND_DIR" && npm run build >/dev/null && npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort) &
else
  (cd "$FRONTEND_DIR" && npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort) &
fi
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
