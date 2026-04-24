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
  if docker info >/dev/null 2>&1; then
    echo "Starting MongoDB (docker compose up -d)..."
    if ! docker compose up -d; then
      echo "Warning: docker compose failed (image pull or compose error). Fix Docker/network, or use Atlas in .env."
    fi
  else
    echo "Docker is installed but the daemon is not running (start Docker Desktop)."
    echo "  Skipping docker compose. Use MongoDB Atlas: set MONGO_URI + MONGO_DB_NAME in .env,"
    echo "  or start Docker and run: docker compose up -d"
  fi
else
  echo "Docker Compose not found — ensure MongoDB is reachable at MONGO_URI in .env."
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
