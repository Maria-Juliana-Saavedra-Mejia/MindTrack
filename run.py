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

from fapi.app import _append_agent_debug_ndjson, build_app

app = build_app()


def _lsof_listen(port: int) -> str:
    try:
        import subprocess

        r = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        return out or err or f"(exit {r.returncode})"
    except Exception as exc:
        return f"lsof_failed: {exc}"


def _try_bind_tcp(port: int) -> bool:
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False


# Prefer 5050–5059 (avoid macOS AirPlay on 5000). If busy, try common high ports (not 443 — privileged).
_FALLBACK_HTTP_PORTS = (8080, 8443, 8888, 3000, 8000)


def _first_available_http_port() -> tuple[int | None, list[int]]:
    """Pick first ports that accept bind on 0.0.0.0 for local HTTP dev."""
    tried: list[int] = []
    for p in range(5050, 5060):
        tried.append(p)
        if _try_bind_tcp(p):
            return p, tried
    for p in _FALLBACK_HTTP_PORTS:
        tried.append(p)
        if _try_bind_tcp(p):
            return p, tried
    return None, tried


if __name__ == "__main__":
    import errno
    import uvicorn

    debug = os.getenv("FLASK_ENV", "development").lower() == "development"
    host = "127.0.0.1"
    port_explicit = "PORT" in os.environ
    if port_explicit:
        port = int(os.environ["PORT"])
    else:
        port, _ = _first_available_http_port()
        if port is None:
            raise RuntimeError(
                "No free TCP port in 5050–5059 or fallback list "
                f"{_FALLBACK_HTTP_PORTS}. Stop other servers or set PORT explicitly, "
                "e.g. PORT=8080 python3 run.py"
            )
    os.environ["MINDTRACK_HTTP_PORT"] = str(port)
    if not port_explicit and port != 5050:
        print(
            f"\nNote: default port 5050 was busy; starting on {port} instead.\n"
            "  Open the UI at the URL printed below so API + pages share the same port.\n"
            "  If you use Live Server on another port, set that site’s API base to match, e.g.\n"
            f"    ?api=http://127.0.0.1:{port}  (once), or window.MINDTRACK_DEV_API_PORT = \"{port}\"\n"
            "  Or free 5050 and restart, or force: PORT=5050 python3 run.py (will error if busy).\n",
            file=sys.stderr,
        )
    print()
    print("=" * 60)
    print("  MindTrack")
    print(f"  API + UI:  http://{host}:{port}/")
    print(f"  Health:    http://{host}:{port}/health")
    print(f"  File logs: logs/mindtrack.log (created after Mongo connects)")
    print("  On macOS do not open :5000 for MindTrack — AirPlay uses it; default is :5050")
    # Hot reload is opt-in: uvicorn --reload has caused restart loops (dropped API requests)
    # when watched trees or tooling touched files. Stable default avoids ERR_CONNECTION_TIMED_OUT.
    _reload = debug and os.environ.get("UVICORN_RELOAD", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if debug and not _reload:
        print(
            "  Hot reload: off (stable). Set UVICORN_RELOAD=1 to watch backend/app + backend/fapi."
        )
    elif _reload:
        print("  Hot reload: ON — expect restarts when .py files change.")
    print(f"  Uvicorn reload flag: {_reload}")
    print("=" * 60)
    print()
    try:
        # #region agent log
        try:
            _append_agent_debug_ndjson(
                {
                    "sessionId": "1e99b1",
                    "hypothesisId": "H3",
                    "location": "run.py:uvicorn",
                    "message": "uvicorn_start",
                    "data": {
                        "port": port,
                        "reload": _reload,
                        "mindtrack_http_port": os.environ.get(
                            "MINDTRACK_HTTP_PORT"
                        ),
                        "pid": os.getpid(),
                    },
                },
                mirror_stderr=True,
            )
        except Exception:
            pass
        # #endregion
        _reload_kw: dict = {}
        if _reload:
            _reload_kw["reload_dirs"] = [
                os.path.join(_BACKEND, "app"),
                os.path.join(_BACKEND, "fapi"),
            ]
        uvicorn.run(
            "run:app",
            host="0.0.0.0",
            port=port,
            reload=_reload,
            **_reload_kw,
        )
    except OSError as exc:
        if getattr(exc, "errno", None) == errno.EADDRINUSE:
            lsout = _lsof_listen(port)
            print(
                f"\nERROR: Port {port} is already in use (another MindTrack / terminal?).\n"
                "  Stop that process, or run on another port, e.g.:\n"
                "    PORT=5051 python3 run.py\n"
                f"  Processes listening on this port now:\n{lsout or '(lsof produced no rows)'}\n",
                file=sys.stderr,
            )
        raise
