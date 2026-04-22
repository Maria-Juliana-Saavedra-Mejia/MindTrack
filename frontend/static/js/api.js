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
 * - Local dev: Live Server ports (e.g. 5500) -> http://127.0.0.1:5000; else same-origin /api/...
 */
function _normalizeApiBase(s) {
  if (!s || !String(s).trim()) {
    return "";
  }
  const t = String(s)
    .trim()
    .replace(/\/$/, "");
  if (!/^https?:\/\//i.test(t)) {
    return "";
  }
  return t;
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
  const port = window.location.port;
  if (["5500", "5501", "3000", "3001", "5173", "8080"].includes(port)) {
    return "http://127.0.0.1:5000";
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
        "Flask server URL (https://...)."
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
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("mindtrack_user");
    window.location.href = appHomeUrl();
    throw new Error(data.message || "Unauthorized");
  }
  if (!response.ok) {
    throw new Error(data.message || "Request failed");
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
