#!/usr/bin/env bash
# Local “deploy”: optional Mongo via Docker, venv + deps, then MindTrack (FastAPI + UI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "MindTrack local deploy — repo: $ROOT"

if [[ ! -f .env ]]; then
  echo "No .env found; copying .env.example -> .env"
  cp .env.example .env
  echo "  Edit .env if you use MongoDB Atlas instead of localhost:27017."
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Starting MongoDB (docker compose up -d)..."
  docker compose up -d
else
  echo "Docker Compose not available — ensure MongoDB is running at MONGO_URI from .env."
fi

PY="${PYTHON:-python3}"
if [[ ! -d .venv ]]; then
  echo "Creating .venv with $PY ..."
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt

echo ""
echo "Starting API + web UI (Ctrl+C to stop). Open the URL printed below."
exec python run.py
