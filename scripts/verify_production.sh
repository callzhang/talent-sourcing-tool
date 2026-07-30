#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTION_URL="${PRODUCTION_URL:-https://talent-sourcing-tool-zeta.vercel.app}"
PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-$PRODUCTION_URL}"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "== Install frontend dependencies =="
  npm --prefix "$ROOT_DIR/frontend" ci
  echo
fi

echo "== Deployment package hygiene =="
python3 "$ROOT_DIR/scripts/check_deploy_hygiene.py"

echo
echo "== Production readiness =="
if ! python3 "$ROOT_DIR/scripts/check_production_readiness.py" --strict "$@"; then
  echo
  echo "Production readiness failed; skipping production smoke E2E."
  exit 1
fi

echo
echo "== Install Playwright browser =="
npm --prefix "$ROOT_DIR/frontend" run test:e2e:install >/dev/null

echo
echo "== Production smoke E2E =="
PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" \
  npm --prefix "$ROOT_DIR/frontend" run test:e2e -- --grep "Production smoke"
