# backend/tests/test_api_route_alignment.py
"""Static check: every path the frontend calls via apiFetch exists on FastAPI."""

from fapi.app import build_app

# (method, path) — from frontend/static/js/*.js, frontend/templates/*.html
_FRONTEND_API_ROUTES = [
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/me"),
    ("GET", "/api/habits"),
    ("POST", "/api/habits"),
    ("GET", "/api/habits/{habit_id}"),
    ("PUT", "/api/habits/{habit_id}"),
    ("DELETE", "/api/habits/{habit_id}"),
    ("GET", "/api/logs"),
    ("POST", "/api/logs"),
    ("DELETE", "/api/logs/{log_id}"),
    ("GET", "/api/logs/streak/{habit_id}"),
    ("GET", "/api/logs/summary"),
    ("GET", "/api/ai/insights"),
    ("POST", "/api/ai/generate"),
]


def _registered_api_endpoints(app):
    """Map path -> set of HTTP methods for /api/* routes."""
    by_path = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api"):
            continue
        methods = getattr(route, "methods", None) or set()
        for m in methods:
            if m == "HEAD":
                continue
            by_path.setdefault(path, set()).add(m)
    return by_path


def test_fastapi_paths_match_frontend_api_fetch_calls():
    app = build_app()
    registered = _registered_api_endpoints(app)
    missing = []
    for method, path in _FRONTEND_API_ROUTES:
        methods = registered.get(path)
        if not methods or method not in methods:
            missing.append((method, path, sorted(methods or [])))
    assert not missing, "Missing or wrong method on routes: " + repr(missing)


def test_no_duplicate_api_prefix_in_documented_url_shape():
    """Guardrail: app paths must use a single /api segment (avoid /api/api/...)."""
    app = build_app()
    bad = [
        getattr(r, "path", "")
        for r in app.routes
        if getattr(r, "path", "").startswith("/api/api/")
    ]
    assert not bad, "Unexpected double /api prefix: " + repr(bad)
