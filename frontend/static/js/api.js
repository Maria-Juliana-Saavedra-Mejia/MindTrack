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

/** Fixed local API base when not using explicit meta/window/?api overrides (no port probing).
 * Must match run.py's first choice (5050–5059); run.py binds the first free port in that range.
 * Override per-machine: meta mindtrack-dev-api-port, window.MINDTRACK_DEV_API_PORT, or ?mt_api_port=. */
const MINDTRACK_FIXED_LOCAL_API_BASE = "http://127.0.0.1:5050";

/**
 * API base (no trailing slash), first match wins:
 * - window.MINDTRACK_API_BASE, then MINDTRACK_DEFAULT_API, then meta mindtrack-api-base
 *   (each skipped if “stale” vs unified loopback port 5050–5059, same as localStorage)
 * - ?api=https://host (saved to localStorage unless stale vs unified port 5050–5059; query stripped from bar)
 * - ?mt_api_port=5051 on loopback — shorthand for ?api=http://127.0.0.1:5051 (Live Server + run.py)
 * - localStorage mindtrack_api_base (ignored if stale: another 5050–5059 slot than the current page)
 * - Local dev on loopback with another port (e.g. Live Server) -> MINDTRACK_FIXED_LOCAL_API_BASE.
 *   If the page is already on the same origin as that base (run.py on 5050, etc.), relative /api calls are used.
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

/**
 * Local MindTrack (run.py) listens on HTTP. If the page is http:// and localStorage / ?api=
 * pinned https://127.0.0.1:505x, requests fail (TLS on a plain-HTTP port). Rewrite to http://
 * for loopback + ports 5050–5059 only.
 *
 * We do NOT rewrite http→https when the page is https://: that would not make run.py work
 * without a TLS listener. Mixed content (https page → http API) must be fixed by opening
 * the UI over http:// or running HTTPS on both ends with real certs.
 */
function _alignLoopbackMindtrackDevApiProtocolWithPage(normalizedBase) {
  if (!normalizedBase) {
    return normalizedBase;
  }
  try {
    const pageProto =
      typeof window !== "undefined" && window.location
        ? window.location.protocol
        : "";
    if (pageProto !== "http:") {
      return normalizedBase;
    }
    const u = new URL(normalizedBase);
    if (!_isLoopbackHost(u.hostname)) {
      return normalizedBase;
    }
    let pn;
    if (u.port) {
      pn = parseInt(u.port, 10);
    } else if (u.protocol === "https:") {
      pn = 443;
    } else if (u.protocol === "http:") {
      pn = 80;
    } else {
      return normalizedBase;
    }
    if (Number.isNaN(pn) || pn < 5050 || pn > 5059) {
      return normalizedBase;
    }
    if (u.protocol !== "https:") {
      return normalizedBase;
    }
    const v = new URL(normalizedBase);
    v.protocol = "http:";
    return _normalizeApiBase(v.href);
  } catch (e) {
    return normalizedBase;
  }
}

function _finalizeMindtrackApiBase(normalizedBase, persistIfAligned) {
  const aligned = _alignLoopbackMindtrackDevApiProtocolWithPage(normalizedBase);
  if (
    persistIfAligned &&
    aligned &&
    normalizedBase &&
    aligned !== normalizedBase &&
    typeof localStorage !== "undefined"
  ) {
    try {
      localStorage.setItem("mindtrack_api_base", aligned);
    } catch (e) {
      /* private mode */
    }
  }
  return aligned;
}

function _isLoopbackHost(hostname) {
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]" ||
    hostname === "::1" ||
    hostname === "0.0.0.0"
  );
}

/**
 * True when mindtrack_api_base points at another port in run.py's primary range (5050–5059)
 * while the page is already on loopback in that range — e.g. saved :5050 but UI is :5051.
 * Used for explicit window/meta API bases only (user intent).
 */
function _isStaleUnifiedMindtrackApiBase(storedBase, pageHostname, pagePortStr) {
  if (!storedBase || !pagePortStr) {
    return false;
  }
  if (!_isLoopbackHost(pageHostname)) {
    return false;
  }
  const pagePn = parseInt(pagePortStr, 10);
  if (
    Number.isNaN(pagePn) ||
    pagePn < 5050 ||
    pagePn > 5059
  ) {
    return false;
  }
  try {
    const u = new URL(storedBase);
    if (!_isLoopbackHost(u.hostname)) {
      return false;
    }
    let storedPn;
    if (u.port) {
      storedPn = parseInt(u.port, 10);
    } else if (u.protocol === "https:") {
      storedPn = 443;
    } else if (u.protocol === "http:") {
      storedPn = 80;
    } else {
      return false;
    }
    if (
      Number.isNaN(storedPn) ||
      storedPn < 5050 ||
      storedPn > 5059
    ) {
      return false;
    }
    return storedPn !== pagePn;
  } catch (e) {
    return false;
  }
}

/**
 * True when localStorage / ?api= pins the default loopback API port (5050) but the page is on
 * another loopback port (e.g. Live Server :5500). Other unified slots (5051…) may be probe results.
 * Not used for meta / window overrides.
 */
function _isLiveServerStaleUnifiedStoredPin(storedBase, pageHostname, pagePortStr) {
  if (!storedBase) {
    return false;
  }
  if (!_isLoopbackHost(pageHostname)) {
    return false;
  }
  let pagePn;
  if (!pagePortStr) {
    /* browsers omit port for :80/:443 — not MindTrack's unified 5050–5059 slot */
    pagePn = -1;
  } else {
    pagePn = parseInt(pagePortStr, 10);
    if (Number.isNaN(pagePn)) {
      return false;
    }
    if (pagePn >= 5050 && pagePn <= 5059) {
      return false;
    }
  }
  try {
    const u = new URL(storedBase);
    if (!_isLoopbackHost(u.hostname)) {
      return false;
    }
    let sp;
    if (u.port) {
      sp = parseInt(u.port, 10);
    } else if (u.protocol === "https:") {
      sp = 443;
    } else if (u.protocol === "http:") {
      sp = 80;
    } else {
      return false;
    }
    if (Number.isNaN(sp) || sp < 5050 || sp > 5059) {
      return false;
    }
    return sp === 5050;
  } catch (e) {
    return false;
  }
}

function _isStaleStoredMindtrackApiBase(storedBase, pageHostname, pagePortStr) {
  return (
    _isStaleUnifiedMindtrackApiBase(storedBase, pageHostname, pagePortStr) ||
    _isLiveServerStaleUnifiedStoredPin(storedBase, pageHostname, pagePortStr)
  );
}

/**
 * Loopback URL whose port is in run.py's primary range (5050–5059). Often a stale ?api= guess
 * when the HTML is served from Live Server (page port not in that range).
 */
function _isLoopbackUrlInPrimaryUnifiedRange(normalizedBase) {
  try {
    const u = new URL(normalizedBase);
    if (!_isLoopbackHost(u.hostname)) {
      return false;
    }
    let pn;
    if (u.port) {
      pn = parseInt(u.port, 10);
    } else if (u.protocol === "https:") {
      pn = 443;
    } else if (u.protocol === "http:") {
      pn = 80;
    } else {
      return false;
    }
    if (Number.isNaN(pn) || pn < 5050 || pn > 5059) {
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Loopback URL for the local FastAPI dev server (run.py 5050–5059).
 * window.MINDTRACK_DEV_API_PORT wins; else meta mindtrack-dev-api-port (injected in base.html);
 * else MINDTRACK_FIXED_LOCAL_API_BASE.
 */
function _computeMindtrackLocalDevApiBase() {
  let fixed = MINDTRACK_FIXED_LOCAL_API_BASE;
  try {
    const wdp =
      typeof window !== "undefined" && window.MINDTRACK_DEV_API_PORT != null
        ? String(window.MINDTRACK_DEV_API_PORT).trim()
        : "";
    if (wdp && /^\d+$/.test(wdp)) {
      const pn = parseInt(wdp, 10);
      if (!Number.isNaN(pn) && pn >= 1 && pn <= 65535) {
        fixed = "http://127.0.0.1:" + pn;
      }
    } else {
      const dm = document.querySelector('meta[name="mindtrack-dev-api-port"]');
      const metaPort =
        dm && dm.getAttribute("content")
          ? String(dm.getAttribute("content")).trim()
          : "";
      if (metaPort && /^\d+$/.test(metaPort)) {
        const pn = parseInt(metaPort, 10);
        if (!Number.isNaN(pn) && pn >= 1 && pn <= 65535) {
          fixed = "http://127.0.0.1:" + pn;
        }
      }
    }
  } catch (e) {
    /* */
  }
  return fixed;
}

/**
 * When the page is on Live Server (etc.), not on 5050–5059, a saved mindtrack_api_base
 * like http://127.0.0.1:5052 is never cleared by unified-slot stale rules — drop it if it
 * disagrees with meta/window/default so fetch targets the real run.py port.
 */
function _invalidateWrongUnifiedPortMindtrackStorage(ph, pp, storedBase) {
  if (!_isLoopbackHost(ph) || !storedBase) {
    return false;
  }
  if (!_isLoopbackUrlInPrimaryUnifiedRange(storedBase)) {
    return false;
  }
  const pagePn = pp === "" ? NaN : parseInt(pp, 10);
  const onDirectMindtrackPort =
    pp !== "" &&
    !Number.isNaN(pagePn) &&
    pagePn >= 5050 &&
    pagePn <= 5059;
  if (onDirectMindtrackPort) {
    return false;
  }
  try {
    const have = new URL(storedBase);
    const prefer = new URL(_computeMindtrackLocalDevApiBase());
    if (String(have.port || "") !== String(prefer.port || "")) {
      try {
        localStorage.removeItem("mindtrack_api_base");
      } catch (e) {
        /* private mode */
      }
      return true;
    }
  } catch (e) {
    /* */
  }
  return false;
}

/** Set localStorage mindtrack_debug_api=1, or ?mt_debug_api=1, or window.MINDTRACK_DEBUG_API=true to log every API request. */
function mindtrackApiDebugEnabled() {
  try {
    if (typeof window !== "undefined" && window.MINDTRACK_DEBUG_API === true) {
      return true;
    }
    if (
      typeof localStorage !== "undefined" &&
      localStorage.getItem("mindtrack_debug_api") === "1"
    ) {
      return true;
    }
    if (
      typeof window !== "undefined" &&
      window.location &&
      new URLSearchParams(window.location.search || "").get("mt_debug_api") === "1"
    ) {
      return true;
    }
  } catch (e) {
    /* */
  }
  return false;
}

function getApiBase() {
  const ph =
    typeof window !== "undefined" && window.location
      ? window.location.hostname
      : "";
  const pp =
    typeof window !== "undefined" && window.location
      ? String(window.location.port || "")
      : "";

  function explicitBaseOrNull(raw) {
    const out = _normalizeApiBase(raw);
    if (!out) {
      return null;
    }
    if (_isStaleUnifiedMindtrackApiBase(out, ph, pp)) {
      return null;
    }
    return out;
  }

  if (
    typeof window.MINDTRACK_API_BASE === "string" &&
    window.MINDTRACK_API_BASE.trim()
  ) {
    const o = explicitBaseOrNull(window.MINDTRACK_API_BASE);
    if (o) {
      return _finalizeMindtrackApiBase(o, false);
    }
  }
  if (
    typeof window.MINDTRACK_DEFAULT_API === "string" &&
    window.MINDTRACK_DEFAULT_API.trim()
  ) {
    const o = explicitBaseOrNull(window.MINDTRACK_DEFAULT_API);
    if (o) {
      return _finalizeMindtrackApiBase(o, false);
    }
  }
  const meta = document.querySelector('meta[name="mindtrack-api-base"]');
  const fromMeta = meta && meta.getAttribute("content");
  if (fromMeta && fromMeta.trim()) {
    const o = explicitBaseOrNull(fromMeta);
    if (o) {
      return _finalizeMindtrackApiBase(o, false);
    }
  }
  try {
    const sp = new URLSearchParams(window.location.search || "");
    let q = sp.get("api");
    if (!q || !String(q).trim()) {
      const mtp = sp.get("mt_api_port");
      if (mtp && String(mtp).trim()) {
        const trimmed = String(mtp).trim();
        if (/^\d+$/.test(trimmed) && _isLoopbackHost(ph)) {
          const pn = parseInt(trimmed, 10);
          if (
            !Number.isNaN(pn) &&
            pn >= 1 &&
            pn <= 65535
          ) {
            const probeHost = _httpLoopbackHostForFetch(
              _canonicalLoopbackProbeHost(ph)
            );
            q = "http://" + probeHost + ":" + pn;
          }
        }
      }
    }
    if (q && String(q).trim()) {
      const b = _normalizeApiBase(String(q));
      if (b) {
        const queryStale = _isStaleStoredMindtrackApiBase(b, ph, pp);
        try {
          const u = new URL(window.location.href);
          let changed = false;
          if (u.searchParams.has("api")) {
            u.searchParams.delete("api");
            changed = true;
          }
          if (u.searchParams.has("mt_api_port")) {
            u.searchParams.delete("mt_api_port");
            changed = true;
          }
          if (changed) {
            const qs = u.searchParams.toString();
            const clean = u.pathname + (qs ? "?" + qs : "") + u.hash;
            history.replaceState(null, "", clean);
          }
        } catch (e) {
          /* not in browser or URL API missing */
        }
        if (queryStale) {
          try {
            localStorage.removeItem("mindtrack_api_base");
          } catch (e) {
            /* private mode */
          }
          /* Same as stale localStorage: do not pin API to another unified-slot port. */
        } else {
          try {
            localStorage.setItem("mindtrack_api_base", b);
          } catch (e) {
            /* private mode */
          }
          return _finalizeMindtrackApiBase(b, true);
        }
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
      const stale = _isStaleStoredMindtrackApiBase(b, ph, pp);
      if (stale) {
        try {
          localStorage.removeItem("mindtrack_api_base");
        } catch (e) {
          /* private mode */
        }
      } else {
        if (_invalidateWrongUnifiedPortMindtrackStorage(ph, pp, b)) {
          /* cleared stale pin; fall through to _computeMindtrackLocalDevApiBase() */
        } else {
          return _finalizeMindtrackApiBase(b, true);
        }
      }
    }
  } catch (e) {
    /* private mode */
  }
  const h = window.location.hostname;
  const p = String(window.location.port || "");
  const isLoopback =
    h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h === "0.0.0.0";
  const fixed = _computeMindtrackLocalDevApiBase();
  const pagePortNum = parseInt(p, 10);
  const onMindtrackUnifiedPort =
    p !== "" &&
    !Number.isNaN(pagePortNum) &&
    pagePortNum >= 5050 &&
    pagePortNum <= 5059;
  /* UI served from python run.py on 5050–5059 — same origin as that server. */
  if (isLoopback && onMindtrackUnifiedPort) {
    return "";
  }
  /* Same origin as fixed API (e.g. http://127.0.0.1:5050 — also when hostname is 0.0.0.0). */
  if (isLoopback && p) {
    try {
      if (
        typeof window !== "undefined" &&
        window.location &&
        window.location.origin === new URL(fixed).origin
      ) {
        return "";
      }
    } catch (e) {
      /* */
    }
  }
  /* Live Server / other loopback port — call API at fixed base (no port scan). */
  if (isLoopback && p) {
    return _finalizeMindtrackApiBase(fixed, false);
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
  if (base) {
    return `${base}${p}`;
  }
  /* Do not fetch against http://0.0.0.0 — use 127.0.0.1 (same machine, reliable in browsers). */
  if (
    typeof window !== "undefined" &&
    window.location &&
    window.location.hostname === "0.0.0.0"
  ) {
    const proto = window.location.protocol;
    const port = window.location.port;
    return `${proto}//127.0.0.1${port ? ":" + port : ""}${p}`;
  }
  return p;
}

function _staticSiteNeedsExplicitApi() {
  const h = (window.location && window.location.hostname) || "";
  return h.endsWith(".github.io") || h === "github.io";
}

/** Brackets IPv6 literals for URL strings (fetch / localStorage base). */
function _httpLoopbackHostForFetch(hostname) {
  if (
    hostname.indexOf(":") >= 0 &&
    hostname.indexOf("[") !== 0
  ) {
    return "[" + hostname + "]";
  }
  return hostname;
}

/** One IPv4 loopback identity for probing so localhost vs 127.0.0.1 behave the same. */
function _canonicalLoopbackProbeHost(hostname) {
  if (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "0.0.0.0"
  ) {
    return "127.0.0.1";
  }
  if (hostname === "[::1]" || hostname === "::1") {
    return "[::1]";
  }
  return hostname;
}

/** Port probing removed — fixed API base in getApiBase (kept as no-op for callers). */
function _maybeProbeMindtrackListenPort() {
  return Promise.resolve();
}

/**
 * Browsers block active mixed content: an https:// page cannot fetch http:// (including loopback).
 * Fail fast with a clear message instead of a generic "Could not reach" after fetch throws.
 */
function _throwIfHttpsPageBlocksHttpApi(resolvedUrl) {
  if (typeof window === "undefined" || !window.location) {
    return;
  }
  if (window.location.protocol !== "https:") {
    return;
  }
  let req;
  try {
    req = new URL(resolvedUrl, window.location.href);
  } catch (e) {
    return;
  }
  if (req.protocol !== "http:") {
    return;
  }
  if (_isLoopbackHost(req.hostname)) {
    try {
      localStorage.removeItem("mindtrack_api_base");
    } catch (e) {
      /* private mode */
    }
    throw new Error(
      "This page is https but the API URL is http on your computer (e.g. 127.0.0.1). " +
        "Browsers block that. For GitHub Pages set Actions secret MINDTRACK_API_BASE to your " +
        "deployed https:// API (Render, etc.). Or open MindTrack at the http:// address printed by " +
        "run.py on your machine—not github.io."
    );
  }
  throw new Error(
    "This page is https but the API URL is http. Use an https:// API root " +
      "(mindtrack-api-base / MINDTRACK_API_BASE / Actions secret), with no /api suffix."
  );
}

async function apiFetch(endpoint, method = "GET", body = null) {
  await _maybeProbeMindtrackListenPort();
  if (
    !String(endpoint).startsWith("http") &&
    _staticSiteNeedsExplicitApi() &&
    !getApiBase()
  ) {
    throw new Error(
      "API URL is not set for this host. GitHub Pages has no backend. " +
        "1) GitHub repo → Settings → Secrets and variables → Actions → New repository secret: " +
        "name MINDTRACK_API_BASE, value your deployed API root (https://..., no /api). " +
        "2) Actions → Deploy GitHub Pages → run workflow again. " +
        "Or edit index.html: meta mindtrack-api-base or window.MINDTRACK_DEFAULT_API to that same https URL."
    );
  }
  const url = apiUrl(endpoint);
  _throwIfHttpsPageBlocksHttpApi(url);
  if (mindtrackApiDebugEnabled()) {
    console.log("[MindTrack API] request", {
      method,
      endpoint,
      resolvedUrl: url,
      apiBase: getApiBase() || "(same-origin)",
      pageUrl:
        typeof window !== "undefined" ? window.location.href : "",
    });
  }
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
    let storedApi = null;
    try {
      storedApi = localStorage.getItem("mindtrack_api_base");
    } catch (e) {
      /* */
    }
    console.error("[MindTrack API] fetch failed (network or blocked)", {
      resolvedUrl: url,
      method,
      endpoint,
      apiBaseResolved: getApiBase() || "(empty → relative to current page origin)",
      mindtrack_api_base_localStorage: storedApi,
      pageHostname:
        typeof window !== "undefined" ? window.location.hostname : "",
      pagePort: typeof window !== "undefined" ? window.location.port : "",
      pageProtocol:
        typeof window !== "undefined" ? window.location.protocol : "",
      errorMessage: err && err.message,
      cause: err && err.cause,
      hintIfPort5000MacOS:
        String(url).indexOf(":5000") >= 0
          ? "macOS often serves AirPlay on :5000 (not your API). Expected API: " +
            _computeMindtrackLocalDevApiBase() +
            "."
          : undefined,
    });
    const health = String(url).replace(/\/api\/.*$/, "/health");
    const tryBase = _computeMindtrackLocalDevApiBase();
    throw new Error(
      "Could not reach the API: " + url + ". 1) Start FastAPI at " + tryBase + " (e.g. uvicorn). " +
        "2) Open " + health + " in the browser. " +
        "3) Mixed content: an https:// page cannot fetch an http:// API — open the UI over http:// or use HTTPS for both. " +
        "(On an http:// page, a saved https:// API on loopback :5050–5059 may be rewritten to http:// automatically.)",
      { cause: err }
    );
  }
  const ct = (response.headers.get("content-type") || "").toLowerCase();
  const rawBody = await response.text();
  let data = {};
  if (rawBody) {
    const trim = rawBody.trim();
    const looksJson =
      ct.includes("application/json") ||
      ct.includes("+json") ||
      /^[\[{]/.test(trim);
    if (looksJson) {
      try {
        data = JSON.parse(rawBody);
      } catch (e) {
        data = {};
      }
    } else if (!response.ok) {
      data = { message: trim.slice(0, 500) };
    }
  }
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
    const suffix = response.status ? " (" + response.status + ")" : "";
    throw new Error((errText || "Request failed") + suffix);
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
