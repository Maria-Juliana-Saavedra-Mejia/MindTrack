/* Fills #user-name / #user-initials from localStorage or GET /api/auth/me (after token hash handoff). */
(function mindtrackUserHeader() {
  const nameEl = document.getElementById("user-name");
  const avEl = document.getElementById("user-initials");
  if (!nameEl || !avEl) {
    return;
  }

  function render(user) {
    const u = user && user.full_name ? user : { full_name: "Student" };
    nameEl.textContent = u.full_name || "Student";
    const initials = (u.full_name || "MT")
      .split(" ")
      .map((p) => p[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    avEl.textContent = initials;
  }

  if (!localStorage.getItem("access_token")) {
    return;
  }
  const user = JSON.parse(localStorage.getItem("mindtrack_user") || "{}");
  if (user && user.full_name) {
    render(user);
  } else {
    (async function loadProfile() {
      try {
        const r = await apiFetch("/api/auth/me", "GET");
        if (r && r.user) {
          localStorage.setItem("mindtrack_user", JSON.stringify(r.user));
          render(r.user);
        } else {
          render({});
        }
      } catch (e) {
        render({});
      }
    })();
  }

  const THEME_KEY = "mindtrack_theme";
  const COMPACT_KEY = "mindtrack_compact_ui";

  function applyThemeFromStorage() {
    try {
      const saved = localStorage.getItem(THEME_KEY);
      if (saved === "dark" || saved === "light") {
        document.documentElement.setAttribute("data-theme", saved);
      }
    } catch (e) {
      /* */
    }
  }

  function applyCompactFromStorage() {
    try {
      document.documentElement.classList.toggle(
        "mindtrack-compact",
        localStorage.getItem(COMPACT_KEY) === "1"
      );
    } catch (e) {
      /* */
    }
  }

  applyThemeFromStorage();
  applyCompactFromStorage();
})();
