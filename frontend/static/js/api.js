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
 *   (each skipped if “stale” vs unified loopback port 5050–5059, same as localStorage)
 * - ?api=https://host (saved to localStorage unless stale vs unified port 5050–5059; query stripped from bar)
 * - ?mt_api_port=5051 on loopback — shorthand for ?api=http://127.0.0.1:5051 (Live Server + run.py)
 * - localStorage mindtrack_api_base (ignored if stale: another 5050–5059 slot than the current page)
 * - Local dev on loopback, page on a *different* port than the API (e.g. Live Server) -> same host + MINDTRACK_DEV_API_PORT, or meta mindtrack-dev-api-port, or 5050. If the page is already on 5050–5059 (run.py’s range), same origin is used so 5051 when 5050 is busy still works.
   *   macOS AirPlay Receiver often binds :5000 — we default to 5050 to avoid it; override with MINDTRACK_DEV_API_PORT if you use another API port.
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
        return _finalizeMindtrackApiBase(b, true);
      }
    }
  } catch (e) {
    /* private mode */
  }
  const h = window.location.hostname;
  const p = String(window.location.port || "");
  const isLoopback =
    h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h === "0.0.0.0";
  let devApiPort = "5050";
  try {
    const metaDev = document.querySelector(
      'meta[name="mindtrack-dev-api-port"]'
    );
    const mc = metaDev && metaDev.getAttribute("content");
    if (mc && String(mc).trim()) {
      const t = String(mc).trim();
      if (/^\d+$/.test(t)) {
        devApiPort = t;
      }
    }
  } catch (e) {
    /* */
  }
  try {
    if (
      typeof window !== "undefined" &&
      typeof window.MINDTRACK_DEV_API_PORT === "string" &&
      window.MINDTRACK_DEV_API_PORT.trim()
    ) {
      devApiPort = window.MINDTRACK_DEV_API_PORT.trim();
    }
  } catch (e) {
    /* */
  }
  /* run.py binds API+UI on the first free port in 5050–5059. If 5050 is busy and you open
   * http://127.0.0.1:5051/, do not rewrite the API to :5050 (wrong port — timeouts).
   * Redirect to devApiPort only when the page is on another dev server (e.g. Live Server).
   * devApiPort: window.MINDTRACK_DEV_API_PORT > meta mindtrack-dev-api-port > default 5050. */
  const pagePortNum = parseInt(p, 10);
  const onMindtrackUnifiedPort =
    p !== "" &&
    !Number.isNaN(pagePortNum) &&
    pagePortNum >= 5050 &&
    pagePortNum <= 5059;
  if (
    isLoopback &&
    p &&
    !onMindtrackUnifiedPort &&
    p !== devApiPort
  ) {
    return _finalizeMindtrackApiBase(
      window.location.protocol + "//" + h + ":" + devApiPort,
      false
    );
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

let _mindtrackPortProbePromise = null;
let _mindtrackPortProbeSucceeded = false;
/** True after a full cross-port probe finished with no responding MindTrack (see logs H1). */
let _mindtrackProbeExhaustedNoMatch = false;

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

/** User pinned API via HTML/URL/storage — do not block on failed port scan. */
function _hasExplicitMindtrackApiHint() {
  try {
    const ph =
      typeof window !== "undefined" && window.location
        ? window.location.hostname
        : "";
    const pp =
      typeof window !== "undefined" && window.location
        ? String(window.location.port || "")
        : "";
    if (
      typeof window !== "undefined" &&
      typeof window.MINDTRACK_API_BASE === "string" &&
      window.MINDTRACK_API_BASE.trim()
    ) {
      return true;
    }
    if (
      typeof window !== "undefined" &&
      typeof window.MINDTRACK_DEFAULT_API === "string" &&
      window.MINDTRACK_DEFAULT_API.trim()
    ) {
      return true;
    }
    if (
      typeof window !== "undefined" &&
      typeof window.MINDTRACK_DEV_API_PORT === "string" &&
      window.MINDTRACK_DEV_API_PORT.trim()
    ) {
      return true;
    }
    const mb = document.querySelector('meta[name="mindtrack-api-base"]');
    if (mb && mb.getAttribute("content") && String(mb.getAttribute("content")).trim()) {
      return true;
    }
    const md = document.querySelector('meta[name="mindtrack-dev-api-port"]');
    if (md && md.getAttribute("content") && String(md.getAttribute("content")).trim()) {
      return true;
    }
    const sp = new URLSearchParams(window.location.search || "");
    if (sp.get("api") && String(sp.get("api")).trim()) {
      return true;
    }
    if (sp.get("mt_api_port") && String(sp.get("mt_api_port")).trim()) {
      return true;
    }
    /* Do not treat stale mindtrack_api_base as “user intent” (same rules as getApiBase). */
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem("mindtrack_api_base");
      const norm = _normalizeApiBase(raw);
      if (
        raw &&
        norm &&
        !_isStaleStoredMindtrackApiBase(norm, ph, pp)
      ) {
        return true;
      }
    }
  } catch (e) {
    /* */
  }
  return false;
}

/** Live Server / preview on loopback with a non-unified port: probe where MindTrack listens. */
function _needsMindtrackListenPortProbe() {
  try {
    const h = window.location.hostname;
    const isLoopback =
      h === "localhost" ||
      h === "127.0.0.1" ||
      h === "[::1]" ||
      h === "0.0.0.0";
    if (!isLoopback) {
      return false;
    }
    const p = String(window.location.port || "");
    if (!p) {
      return false;
    }
    const pagePn = parseInt(p, 10);
    if (
      !Number.isNaN(pagePn) &&
      pagePn >= 5050 &&
      pagePn <= 5059
    ) {
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
}

function _maybeProbeMindtrackListenPort() {
  if (_mindtrackPortProbeSucceeded) {
    return Promise.resolve();
  }
  if (_mindtrackPortProbePromise !== null) {
    return _mindtrackPortProbePromise;
  }
  if (!_needsMindtrackListenPortProbe()) {
    _mindtrackPortProbePromise = Promise.resolve();
    return _mindtrackPortProbePromise;
  }
  try {
    const rawLs = localStorage.getItem("mindtrack_api_base");
    const normLs = _normalizeApiBase(rawLs);
    if (normLs && _isLoopbackUrlInPrimaryUnifiedRange(normLs)) {
      localStorage.removeItem("mindtrack_api_base");
    }
  } catch (e) {
    /* */
  }
  const probeHost = _canonicalLoopbackProbeHost(window.location.hostname);
  const hostFetch = _httpLoopbackHostForFetch(probeHost);
  const ports = [];
  let i;
  for (i = 5050; i <= 5059; i += 1) {
    ports.push(i);
  }
  [8080, 8443, 8888, 3000, 8000].forEach(function (x) {
    ports.push(x);
  });
  _mindtrackPortProbePromise = new Promise(function (resolve) {
    _mindtrackProbeExhaustedNoMatch = false;
    let settled = false;
    let foundPort = false;
    let pending = ports.length;

    function finish() {
      if (!settled) {
        settled = true;
        resolve();
      }
      /* Failed discovery: allow a later apiFetch to probe again (slow server start). */
      if (!foundPort) {
        _mindtrackPortProbePromise = null;
      }
    }

    function tryPort(port) {
      const c = new AbortController();
      const t = setTimeout(function () {
        c.abort();
      }, 1200);
      fetch(
        "http://" + hostFetch + ":" + port + "/mindtrack-http-port",
        {
          method: "GET",
          cache: "no-store",
          signal: c.signal,
        }
      )
        .then(function (r) {
          if (!r.ok) {
            throw new Error("bad");
          }
          return r.text();
        })
        .then(function (text) {
          const n = parseInt(String(text).trim(), 10);
          if (Number.isNaN(n)) {
            throw new Error("nan");
          }
          foundPort = true;
          _mindtrackPortProbeSucceeded = true;
          try {
            localStorage.setItem(
              "mindtrack_api_base",
              "http://" + hostFetch + ":" + n
            );
          } catch (e) {
            /* */
          }
          finish();
        })
        .catch(function () {
          /* */
        })
        .finally(function () {
          clearTimeout(t);
          pending -= 1;
          if (pending <= 0) {
            if (!foundPort) {
              _mindtrackProbeExhaustedNoMatch = true;
            }
            finish();
          }
        });
    }

    ports.forEach(tryPort);
  });
  return _mindtrackPortProbePromise;
}

async function apiFetch(endpoint, method = "GET", body = null) {
  await _maybeProbeMindtrackListenPort();
  if (
    _needsMindtrackListenPortProbe() &&
    !_mindtrackPortProbeSucceeded &&
    _mindtrackProbeExhaustedNoMatch &&
    !_hasExplicitMindtrackApiHint()
  ) {
    throw new Error(
      "MindTrack API was not found on this machine (port scan finished with no response). " +
        "Start the backend from the project folder: python3 run.py — then open the URL it prints in the terminal, " +
        "or add once to this page's address bar: ?api=http://127.0.0.1:PORT (use the PORT shown, e.g. 5050 or 5051)."
    );
  }
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
          ? "macOS often serves AirPlay on :5000 (not your API). Default is :5050; if you use PORT=5000, disable AirPlay or set window.MINDTRACK_DEV_API_PORT = \"5000\" before api.js."
          : undefined,
    });
    const health = String(url).replace(/\/api\/.*$/, "/health");
    throw new Error(
      "Could not reach the API: " + url + ". 1) Run the backend: python run.py. " +
        "2) In the browser open " + health + " (same host/port as the API; use the port run.py printed, e.g. 5050 or 5051). " +
        "3) Scheme mismatch: an https:// page cannot fetch an http:// API (mixed content — the browser blocks it). " +
        "Fix: open the UI over http:// (e.g. the URL from run.py), or terminate TLS in front of the API and use https for both. " +
        "(On an http:// page, a saved https:// API on loopback :5050–5059 is rewritten to http:// automatically.)",
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
