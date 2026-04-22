/* static/js/api.js */
(function mindtrackConsumeAuthHash() {
  function strip() {
    try {
      const u = new URL(window.location.href);
      u.hash = "";
      history.replaceState(null, "", u.pathname + u.search);
    } catch (e) {
      /* */
    }
  }
  try {
    const h = window.location.hash || "";
    if (h.startsWith("#mt_t=")) {
      const t = decodeURIComponent(h.slice(6));
      if (t) {
        localStorage.setItem("access_token", t);
      }
      strip();
      return;
    }
    if (h.startsWith("#mt_auth=")) {
      const raw = decodeURIComponent(h.slice(9));
      const o = JSON.parse(raw);
      if (o && o.access_token) {
        localStorage.setItem("access_token", o.access_token);
        if (o.user) {
          localStorage.setItem("mindtrack_user", JSON.stringify(o.user));
        }
      }
      strip();
    }
  } catch (e) {
    /* malformed hash */
  }
})();

/**
 * API base (no trailing slash), first match wins:
 * - window.MINDTRACK_API_BASE, then MINDTRACK_DEFAULT_API, then meta mindtrack-api-base
 * - ?api=https://host (saved to localStorage; the query is then stripped from the address bar)
 * - localStorage mindtrack_api_base
 * - Local dev on loopback (not port 5000) -> same host:5000; else same-origin /api/... (e.g. API+UI on one host)
 * Deploy: set meta or MINDTRACK_DEFAULT_API to your deployed API; ensure CORS_ORIGINS on the server
 * includes your static site's origin (see backend app config / env).
 */
function _normalizeApiBase(s) {
  if (!s || !String(s).trim()) {
    return "";
  }
  let t = String(s).trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(t)) {
    return "";
  }
  /* Many hosts set the API as https://x.com — if they use https://x.com/api, we would
   * otherwise build https://x.com/api/api/auth/... and get 404. Strip a trailing /api. */
  t = t.replace(/\/api\/?$/i, "");
  return t.replace(/\/$/, "");
}

function getApiBase() {
  if (
    typeof window.MINDTRACK_API_BASE === "string" &&
    window.MINDTRACK_API_BASE.trim()
  ) {
    return _normalizeApiBase(window.MINDTRACK_API_BASE);
  }
  if (
    typeof window.MINDTRACK_DEFAULT_API === "string" &&
    window.MINDTRACK_DEFAULT_API.trim()
  ) {
    return _normalizeApiBase(window.MINDTRACK_DEFAULT_API);
  }
  const meta = document.querySelector('meta[name="mindtrack-api-base"]');
  const fromMeta = meta && meta.getAttribute("content");
  if (fromMeta && fromMeta.trim()) {
    return _normalizeApiBase(fromMeta);
  }
  try {
    const q = new URLSearchParams(window.location.search || "").get("api");
    if (q && String(q).trim()) {
      const b = _normalizeApiBase(String(q));
      if (b) {
        try {
          localStorage.setItem("mindtrack_api_base", b);
        } catch (e) {
          /* private mode */
        }
        try {
          const u = new URL(window.location.href);
          if (u.searchParams.has("api")) {
            u.searchParams.delete("api");
            const qs = u.searchParams.toString();
            const clean = u.pathname + (qs ? "?" + qs : "") + u.hash;
            history.replaceState(null, "", clean);
          }
        } catch (e) {
          /* not in browser or URL API missing */
        }
        return b;
      }
    }
  } catch (e) {
    /* no URL */
  }
  try {
    const stored = localStorage.getItem("mindtrack_api_base");
    const b = _normalizeApiBase(stored);
    if (stored && !b) {
      try {
        localStorage.removeItem("mindtrack_api_base");
      } catch (e) {
        /* private mode */
      }
    }
    if (b) {
      return b;
    }
  } catch (e) {
    /* private mode */
  }
  const h = window.location.hostname;
  const p = String(window.location.port || "");
  const isLoopback =
    h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h === "0.0.0.0";
  if (isLoopback && p && p !== "5000") {
    return window.location.protocol + "//" + h + ":5000";
  }
  return "";
}

function appHomeUrl() {
  if (typeof window.MINDTRACK_BASE === "string" && window.MINDTRACK_BASE) {
    const b = window.MINDTRACK_BASE;
    if (b.endsWith("/")) {
      return b + "index.html";
    }
    return b + "/index.html";
  }
  return "/";
}

function apiUrl(path) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const p = path.startsWith("/") ? path : `/${path}`;
  const base = getApiBase();
  return base ? `${base}${p}` : p;
}

function _staticSiteNeedsExplicitApi() {
  const h = (window.location && window.location.hostname) || "";
  return h.endsWith(".github.io") || h === "github.io";
}

async function apiFetch(endpoint, method = "GET", body = null) {
  if (
    !String(endpoint).startsWith("http") &&
    _staticSiteNeedsExplicitApi() &&
    !getApiBase()
  ) {
    throw new Error(
      "API URL is not set for this host. In index.html set " +
        "MINDTRACK_DEFAULT_API or the mindtrack-api-base meta to your " +
        "API server root (https://...), with no /api suffix."
    );
  }
  const url = apiUrl(endpoint);
  const token = localStorage.getItem("access_token");
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const options = { method, headers };
  if (body && method !== "GET") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    const health = String(url).replace(/\/api\/.*$/, "/health");
    throw new Error(
      "Could not reach the API: " + url + ". 1) Run the backend: python run.py. " +
        "2) In the browser open " + health + " (same host/port as the API, usually :5000). " +
        "3) If the page uses http but the API is https (or the reverse), the browser will block; keep both on http for local dev.",
      { cause: err }
    );
  }
  const data = await response.json().catch(() => ({}));
  let errText = data.message;
  if (!errText && data.detail != null) {
    if (typeof data.detail === "string") {
      errText = data.detail;
    } else if (Array.isArray(data.detail) && data.detail[0]) {
      const d0 = data.detail[0];
      errText = d0.msg || d0.message || String(d0);
    }
  }
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("mindtrack_user");
    window.location.href = appHomeUrl();
    throw new Error(errText || "Unauthorized");
  }
  if (response.status === 404) {
    throw new Error(
      (errText || "Not found") +
        ". Wrong URL: use the API server root in mindtrack-api-base (e.g. https://api.example.com) " +
        "with no /api on the end. If you use GitHub Pages, the request must not go to the Pages host for /api/... ."
    );
  }
  if (!response.ok) {
    throw new Error(errText || "Request failed");
  }
  return data;
}

/**
 * In-app path for GitHub Pages (base path), e.g. "login" -> "/Repo/login" when MINDTRACK_BASE is "/Repo/".
 */
function mindtrackAppPath(path) {
  const b = (window.MINDTRACK_BASE || "/").replace(/\/?$/, "/");
  return b + (path || "").replace(/^\//, "");
}
if (typeof window !== "undefined") {
  window.mindtrackAppPath = mindtrackAppPath;
}
