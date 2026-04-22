# run.py
"""Application entrypoint for MindTrack (FastAPI + Uvicorn)."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from dotenv import load_dotenv

load_dotenv()

from fapi.app import build_app

app = build_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development").lower() == "development"
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
    )
