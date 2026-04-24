/* static/js/profile.js — full profile page (theme + compact + user info) */
(function mindtrackProfilePage() {
  if (!localStorage.getItem("access_token")) {
    window.location.href =
      typeof mindtrackAppPath === "function" ? mindtrackAppPath("login") : "/login";
    return;
  }

  const THEME_KEY = "mindtrack_theme";
  const COMPACT_KEY = "mindtrack_compact_ui";

  function applyTheme(theme) {
    const t = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch (e) {
      /* */
    }
    document.querySelectorAll(".profile-theme-pill").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-theme") === t);
    });
  }

  function applyCompact(on) {
    document.documentElement.classList.toggle("mindtrack-compact", on);
    try {
      localStorage.setItem(COMPACT_KEY, on ? "1" : "0");
    } catch (e) {
      /* */
    }
    const cb = document.getElementById("profile-page-compact");
    if (cb) {
      cb.checked = on;
    }
  }

  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") {
      applyTheme(saved);
    }
  } catch (e) {
    /* */
  }
  try {
    applyCompact(localStorage.getItem(COMPACT_KEY) === "1");
  } catch (e) {
    /* */
  }

  document.querySelectorAll(".profile-theme-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      applyTheme(btn.getAttribute("data-theme") || "light");
    });
  });

  const compactCb = document.getElementById("profile-page-compact");
  if (compactCb) {
    compactCb.addEventListener("change", () => {
      applyCompact(compactCb.checked);
    });
  }

  function initialsFromName(name) {
    return (name || "MT")
      .split(" ")
      .map((p) => p[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }

  function fillUser(user) {
    const u = user && user.full_name ? user : {};
    const nameEl = document.getElementById("profile-page-name");
    const emailEl = document.getElementById("profile-page-email");
    const avEl = document.getElementById("profile-page-avatar");
    const topName = document.getElementById("user-name");
    const topAv = document.getElementById("user-initials");
    const displayName = u.full_name || "Student";
    const email = u.email || "";
    if (nameEl) {
      nameEl.textContent = displayName;
    }
    if (emailEl) {
      emailEl.textContent = email || "—";
    }
    if (avEl) {
      avEl.textContent = initialsFromName(displayName);
    }
    if (topName) {
      topName.textContent = displayName;
    }
    if (topAv) {
      topAv.textContent = initialsFromName(displayName);
    }
  }

  let user = JSON.parse(localStorage.getItem("mindtrack_user") || "{}");
  if (user && user.full_name) {
    fillUser(user);
  }
  (async function loadMe() {
    try {
      const r = await apiFetch("/api/auth/me", "GET");
      if (r && r.user) {
        user = r.user;
        localStorage.setItem("mindtrack_user", JSON.stringify(user));
        fillUser(user);
      } else {
        fillUser({});
      }
    } catch (e) {
      fillUser(user);
    }
  })();
})();
