#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$ROOT_DIR/.tmp/hr-e2e"
mkdir -p "$TMP_DIR"

DEFAULT_BACKEND_PORT=18000
DEFAULT_FRONTEND_PORT=15173
BACKEND_PORT="${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}"
FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
DB_PATH="$TMP_DIR/hr-e2e.sqlite3"
WORKSPACE_PATH="$TMP_DIR/review-workspaces"
DEV_LOG="$TMP_DIR/dev.log"

pick_available_port() {
  local preferred_port="$1"
  local host="$2"
  python3 "$ROOT_DIR/scripts/port_utils.py" "$preferred_port" "$host"
}

report_dev_failure() {
  echo "Local dev stack exited before HR E2E finished booting." >&2
  if [[ -f "$DEV_LOG" ]]; then
    echo "--- tail -n 40 $DEV_LOG ---" >&2
    tail -n 40 "$DEV_LOG" >&2 || true
    echo "--- end dev log ---" >&2
  fi
}

cleanup() {
  if [[ -n "${DEV_PID:-}" ]]; then
    kill "$DEV_PID" 2>/dev/null || true
    wait "$DEV_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "== Install frontend dependencies =="
  npm --prefix "$ROOT_DIR/frontend" ci
  echo
fi

wait_for_url() {
  local url="$1"
  local retries="${2:-120}"
  local attempt
  for ((attempt=1; attempt<=retries; attempt++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -n "${DEV_PID:-}" ]] && ! kill -0 "$DEV_PID" 2>/dev/null; then
      report_dev_failure
      return 1
    fi
    sleep 1
  done
  echo "Timed out waiting for $url" >&2
  if [[ -n "${DEV_PID:-}" ]] && ! kill -0 "$DEV_PID" 2>/dev/null; then
    report_dev_failure
  fi
  return 1
}

rm -f "$DB_PATH"
rm -rf "$WORKSPACE_PATH"

export TALENT_DATABASE_URL="sqlite:///$DB_PATH"
export TALENT_REVIEW_PROVIDER="${TALENT_REVIEW_PROVIDER:-codex}"
export TALENT_REVIEW_WORKSPACE_ROOT="$WORKSPACE_PATH"

if [[ -z "${BACKEND_PORT:-}" || "$BACKEND_PORT" == "$DEFAULT_BACKEND_PORT" ]]; then
  BACKEND_PORT="$(pick_available_port "$DEFAULT_BACKEND_PORT" "$BACKEND_HOST")"
fi
if [[ -z "${FRONTEND_PORT:-}" || "$FRONTEND_PORT" == "$DEFAULT_FRONTEND_PORT" ]]; then
  FRONTEND_PORT="$(pick_available_port "$DEFAULT_FRONTEND_PORT" "$FRONTEND_HOST")"
fi

BACKEND_PROXY_TARGET="http://$BACKEND_HOST:$BACKEND_PORT"
PLAYWRIGHT_BASE_URL="http://$FRONTEND_HOST:$FRONTEND_PORT"

echo "Using backend port: $BACKEND_PORT"
echo "Using frontend port: $FRONTEND_PORT"

export BACKEND_PROXY_TARGET
export BACKEND_HOST
export BACKEND_PORT
export BACKEND_RELOAD=0
export FRONTEND_HOST
export FRONTEND_PORT
export FRONTEND_SERVER_MODE=preview

if [[ "$TALENT_REVIEW_PROVIDER" == "codex" ]]; then
  TALENT_CODEX_BINARY="${TALENT_CODEX_BINARY:-codex}"
  if ! command -v "$TALENT_CODEX_BINARY" >/dev/null 2>&1; then
    echo "hr_e2e requires TALENT_CODEX_BINARY=$TALENT_CODEX_BINARY when TALENT_REVIEW_PROVIDER=codex" >&2
    exit 1
  fi
fi

if [[ "$TALENT_REVIEW_PROVIDER" == "openai" ]]; then
  if [[ -z "${TALENT_OPENAI_API_KEY:-}" ]]; then
    echo "hr_e2e requires TALENT_OPENAI_API_KEY when TALENT_REVIEW_PROVIDER=openai" >&2
    exit 1
  fi
fi

bash "$ROOT_DIR/scripts/dev.sh" >"$DEV_LOG" 2>&1 &
DEV_PID=$!

wait_for_url "http://$BACKEND_HOST:$BACKEND_PORT/api/jobs"
wait_for_url "$PLAYWRIGHT_BASE_URL"

echo "== Install Playwright browser =="
npm --prefix "$ROOT_DIR/frontend" run test:e2e:install >/dev/null
echo
PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" npm --prefix "$ROOT_DIR/frontend" run test:e2e -- --grep "HR flow|HR layout"
