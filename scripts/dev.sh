#!/usr/bin/env bash
# One-shot local setup + run. Usage: ./scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d backend/.venv ]; then
  echo "▸ creating backend virtualenv"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  echo "▸ installing frontend dependencies"
  npm --prefix frontend install
fi

trap 'kill 0' EXIT
( cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 ) &
npm --prefix frontend run dev -- --host &
wait
