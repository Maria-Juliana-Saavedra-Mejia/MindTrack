/* static/js/dashboard.js */
let trendChartInstance = null;

function mindtrackLoginUrl() {
  return typeof mindtrackAppPath === "function"
    ? mindtrackAppPath("login")
    : "/login";
}

if (!localStorage.getItem("access_token")) {
  window.location.href = mindtrackLoginUrl();
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await apiFetch("/api/auth/logout", "POST");
  } catch (e) {
    /* ignore */
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("mindtrack_user");
  window.location.href = mindtrackLoginUrl();
});

function escapeHtml(text) {
  if (text == null) {
    return "";
  }
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatInsightTimestamp(iso) {
  if (!iso) {
    return "";
  }
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  } catch (e) {
    return "";
  }
}

function mindtrackCssVar(name, fallback) {
  try {
    const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (raw) {
      return raw;
    }
  } catch (e) {
    /* */
  }
  return fallback;
}

function showToast(message, kind) {
  const existing = document.querySelector(".toast");
  if (existing) {
    existing.remove();
  }
  const t = document.createElement("div");
  t.className = "toast" + (kind === "success" ? " toast--success" : "");
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

async function loadKpis() {
  const habits = await apiFetch("/api/habits?active_only=true");
  const active = habits.habits || [];
  document.getElementById("kpi-active").textContent = active.length;

  const today = new Date();
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const end = new Date(start);
  end.setUTCHours(23, 59, 59, 999);
  const logs = await apiFetch(
    `/api/logs?from=${start.toISOString()}&to=${end.toISOString()}`
  );
  const uniqueHabits = new Set((logs.logs || []).map((l) => l.habit_id));
  document.getElementById("kpi-today").textContent = uniqueHabits.size;

  let longest = 0;
  for (const habit of active) {
    const streakData = await apiFetch(`/api/logs/streak/${habit.id}`);
    longest = Math.max(longest, streakData.streak || 0);
  }
  document.getElementById("kpi-streak").textContent = longest;
}

function chartFontFamily() {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue("--font-body")
    .trim()
    .replace(/^["']|["']$/g, "");
  return raw || "system-ui, sans-serif";
}

async function loadChart() {
  const today = new Date();
  const startFetch = new Date(
    Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  );
  startFetch.setUTCDate(startFetch.getUTCDate() - 2);
  startFetch.setUTCHours(0, 0, 0, 0);
  const endFetch = new Date(
    Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  );
  endFetch.setUTCHours(23, 59, 59, 999);

  const logs = await apiFetch(
    `/api/logs?from=${startFetch.toISOString()}&to=${endFetch.toISOString()}`
  );
  const perDay = {};
  const keys = [];
  for (let i = 0; i < 3; i += 1) {
    const d = new Date(startFetch);
    d.setUTCDate(startFetch.getUTCDate() + i);
    const key = d.toISOString().slice(0, 10);
    keys.push(key);
    perDay[key] = 0;
  }
  (logs.logs || []).forEach((log) => {
    const key = log.logged_at.slice(0, 10);
    if (perDay[key] !== undefined) {
      perDay[key] += 1;
    }
  });
  const labels = keys.map((k) => {
    const [y, m, day] = k.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, day));
    return dt.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  });
  const values = keys.map((k) => perDay[k]);
  const canvas = document.getElementById("trend-chart");
  if (!canvas) {
    return;
  }
  if (typeof Chart === "undefined") {
    canvas.style.display = "none";
    const p = document.createElement("p");
    p.className = "chart-fallback-msg";
    p.textContent =
      "Chart library did not load (network or CDN blocked). KPIs and quick log still work.";
    canvas.parentElement.insertBefore(p, canvas.nextSibling);
    return;
  }
  if (trendChartInstance) {
    trendChartInstance.destroy();
    trendChartInstance = null;
  }
  const ctx = canvas.getContext("2d");
  const ff = chartFontFamily();
  const gridColor = mindtrackCssVar("--chart-grid", "rgba(100, 116, 139, 0.12)");
  const lineColor = mindtrackCssVar("--chart-line", "#059669");
  const fillColor = mindtrackCssVar("--chart-fill", "rgba(5, 150, 105, 0.14)");
  const pointBorder = mindtrackCssVar("--chart-point-border", lineColor);
  const pointBg = mindtrackCssVar("--chart-point-bg", "#ffffff");
  const tickColor = mindtrackCssVar("--color-muted", "#64748b");
  const tooltipBg = mindtrackCssVar("--color-surface", "rgba(15, 23, 42, 0.95)");
  const tooltipFg = mindtrackCssVar("--color-text", "#f8fafc");
  trendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Completions",
          data: values,
          borderColor: lineColor,
          backgroundColor: fillColor,
          tension: 0.35,
          fill: true,
          borderWidth: 2.5,
          pointRadius: 5,
          pointHoverRadius: 8,
          pointBackgroundColor: pointBg,
          pointBorderColor: pointBorder,
          pointBorderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 8, right: 8, bottom: 4, left: 4 } },
      font: { family: ff },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: tooltipBg,
          titleColor: tooltipFg,
          bodyColor: tooltipFg,
          titleFont: { family: ff, size: 13 },
          bodyFont: { family: ff, size: 13 },
          padding: 10,
          cornerRadius: 8,
          borderColor: mindtrackCssVar("--color-border", "rgba(148, 163, 184, 0.3)"),
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          grid: { color: gridColor, drawTicks: true },
          ticks: {
            maxTicksLimit: 3,
            font: { family: ff, size: 12 },
            color: tickColor,
          },
        },
        y: {
          beginAtZero: true,
          suggestedMax: Math.max(4, ...values, 1),
          grid: { color: gridColor },
          ticks: {
            stepSize: 1,
            precision: 0,
            font: { family: ff, size: 12 },
            color: tickColor,
          },
        },
      },
    },
  });
}

function renderInsight(insight) {
  const body = document.getElementById("insight-body");
  const meta = document.getElementById("insight-meta");
  const hasText =
    insight &&
    (insight.compliment || insight.observation || insight.tip);
  if (!hasText) {
    meta.hidden = true;
    meta.textContent = "";
    body.innerHTML = `
      <div class="insight-empty">
        <strong>No coach note yet.</strong><br />
        Log a habit once for a short welcome message. After a few days of activity, use
        <em>New insight</em> for a fuller note—still useful in your first weeks.
        <ul>
          <li>Complete at least one habit today.</li>
          <li>Come back after more logs for richer patterns.</li>
        </ul>
      </div>`;
    return;
  }
  if (insight.insight_type === "ephemeral" && typeof console !== "undefined") {
    console.debug(
      "[MindTrack] Coach note was served without persisting (see server logs for details)."
    );
  }
  const when = formatInsightTimestamp(insight.generated_at);
  if (when) {
    meta.hidden = false;
    meta.textContent = `Last updated · ${when}`;
  } else {
    meta.hidden = true;
    meta.textContent = "";
  }
  body.innerHTML = `
    <div class="insight-grid">
      <div class="insight-block compliment">
        <div class="insight-icon" aria-hidden="true">✨</div>
        <h4>What is going well</h4>
        <p>${escapeHtml(insight.compliment)}</p>
      </div>
      <div class="insight-block observation">
        <div class="insight-icon" aria-hidden="true">🔍</div>
        <h4>Pattern</h4>
        <p>${escapeHtml(insight.observation)}</p>
      </div>
      <div class="insight-block tip">
        <div class="insight-icon" aria-hidden="true">💡</div>
        <h4>Next step</h4>
        <p>${escapeHtml(insight.tip)}</p>
      </div>
    </div>`;
}

function renderInsightError(message) {
  const body = document.getElementById("insight-body");
  const meta = document.getElementById("insight-meta");
  meta.hidden = true;
  meta.textContent = "";
  body.innerHTML = `
    <div class="insight-error" role="alert">
      ${escapeHtml(message)}
      <div class="insight-error__actions">
        <button type="button" class="btn-ghost btn-insight-retry" id="insight-retry-btn">Try again</button>
      </div>
    </div>`;
  const retry = document.getElementById("insight-retry-btn");
  if (retry) {
    retry.addEventListener("click", () => {
      loadInsight();
    });
  }
}

async function loadInsight() {
  try {
    const data = await apiFetch("/api/ai/insights");
    renderInsight(data.insight);
  } catch (e) {
    const raw = e && e.message ? e.message : "";
    if (typeof console !== "undefined" && console.debug) {
      console.debug("[MindTrack] loadInsight failed", raw);
    }
    renderInsightError(
      "We could not refresh your coach note. Please try again in a moment."
    );
  }
}

const refreshBtn = document.getElementById("refresh-insight");
refreshBtn.addEventListener("click", async () => {
  const label = refreshBtn.querySelector(".btn-insight-label");
  const prev = label ? label.textContent : "";
  refreshBtn.disabled = true;
  if (label) {
    label.textContent = "Generating…";
  }
  try {
    const data = await apiFetch("/api/ai/generate", "POST");
    renderInsight(data.insight);
    showToast("New insight ready.", "success");
  } catch (e) {
    const raw = e && e.message ? e.message : "";
    if (typeof console !== "undefined" && console.debug) {
      console.debug("[MindTrack] New insight request failed", e && e.status, raw);
    }
    const displayMsg =
      "We could not prepare a new coach note right now. Please try again in a moment.";
    renderInsightError(displayMsg);
    showToast(displayMsg);
  } finally {
    refreshBtn.disabled = false;
    if (label) {
      label.textContent = prev || "New insight";
    }
  }
});

function todayUtcRange() {
  const today = new Date();
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const end = new Date(start);
  end.setUTCHours(23, 59, 59, 999);
  return { start, end };
}

async function loadQuickLog() {
  const habits = await apiFetch("/api/habits?active_only=true");
  const { start, end } = todayUtcRange();
  const logsRes = await apiFetch(
    `/api/logs?from=${start.toISOString()}&to=${end.toISOString()}`
  );
  const counts = {};
  (logsRes.logs || []).forEach((l) => {
    const id = l.habit_id;
    counts[id] = (counts[id] || 0) + 1;
  });

  const container = document.getElementById("quick-log");
  container.innerHTML = "";
  const list = habits.habits || [];
  if (!list.length) {
    const empty = document.createElement("p");
    empty.className = "quick-log-sub";
    empty.style.margin = "0";
    empty.textContent = "Add a habit first — then you can log completions here in one tap.";
    container.appendChild(empty);
    return;
  }

  list.forEach((habit) => {
    const row = document.createElement("div");
    row.className = "quick-row";
    const accent = habit.color || "#0F6E56";
    row.style.setProperty("--accent", accent);

    const initial = counts[habit.id] || 0;
    const icon = habit.icon || "🎯";

    row.innerHTML = `
      <div class="quick-row-main">
        <div class="quick-row-title">
          <span class="quick-emoji" aria-hidden="true">${escapeHtml(icon)}</span>
          <span>${escapeHtml(habit.name)}</span>
        </div>
        <div class="quick-meta">${escapeHtml(habit.category || "")}</div>
        <div class="quick-count" data-count-wrap="${habit.id}">
          Today: <span data-count="${habit.id}">${initial}</span>× logged
        </div>
      </div>
      <div class="quick-actions">
        <button type="button" class="btn-quick-log" data-log="${habit.id}" aria-label="Log ${escapeHtml(habit.name)}">
          Log
        </button>
      </div>`;

    const btn = row.querySelector(`[data-log="${habit.id}"]`);
    const countEl = row.querySelector(`[data-count="${habit.id}"]`);

    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await apiFetch("/api/logs", "POST", { habit_id: habit.id, note: "" });
        const n = parseInt(countEl.textContent, 10) || 0;
        countEl.textContent = String(n + 1);
        showToast(`${habit.name} logged.`, "success");
        await loadKpis();
      } catch (e) {
        showToast(e && e.message ? e.message : "Log failed");
      } finally {
        btn.disabled = false;
      }
    });

    container.appendChild(row);
  });
}

document.addEventListener("mindtrack-theme-changed", () => {
  loadChart().catch(() => {});
});

(async function dashboardInit() {
  try {
    await loadKpis();
    await loadChart();
    await loadInsight();
    await loadQuickLog();
  } catch (e) {
    console.error("MindTrack dashboard init:", e);
    const el = document.getElementById("insight-body");
    if (el) {
      renderInsightError(
        "Could not load dashboard data: " +
          (e && e.message ? e.message : String(e))
      );
    }
  }
})();
