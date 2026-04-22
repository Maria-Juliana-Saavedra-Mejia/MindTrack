/* static/js/api.js */
/**
 * API base (no trailing slash):
 * - On GitHub Pages, set <meta name="mindtrack-api-base" content="https://your-api.example.com" />
 *   or assign window.MINDTRACK_API_BASE before this script in index.html.
 * - Local: same port as Flask uses relative /api/...; Live Server (e.g. :5500) uses
 *   http://127.0.0.1:5000 if no meta/global is set.
 */
function getApiBase() {
  if (
    typeof window.MINDTRACK_API_BASE === "string" &&
    window.MINDTRACK_API_BASE.trim()
  ) {
    return window.MINDTRACK_API_BASE.trim().replace(/\/$/, "");
  }
  const meta = document.querySelector('meta[name="mindtrack-api-base"]');
  const fromMeta = meta && meta.getAttribute("content");
  if (fromMeta && fromMeta.trim()) {
    return fromMeta.trim().replace(/\/$/, "");
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

async function apiFetch(endpoint, method = "GET", body = null) {
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
