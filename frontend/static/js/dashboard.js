/* static/js/dashboard.js */
if (!localStorage.getItem("access_token")) {
  window.location.href = mindtrackAppPath("login");
}

const user = JSON.parse(localStorage.getItem("mindtrack_user") || "{}");
document.getElementById("user-name").textContent = user.full_name || "Student";
const initials = (user.full_name || "MT")
  .split(" ")
  .map((p) => p[0])
  .join("")
  .slice(0, 2)
  .toUpperCase();
document.getElementById("user-initials").textContent = initials;

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await apiFetch("/api/auth/logout", "POST");
  } catch (e) {
    /* ignore */
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("mindtrack_user");
  window.location.href = mindtrackAppPath("login");
});

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

async function loadChart() {
  const end = new Date();
  const start = new Date();
  start.setUTCDate(end.getUTCDate() - 29);
  const logs = await apiFetch(
    `/api/logs?from=${start.toISOString()}&to=${end.toISOString()}`
  );
  const perDay = {};
  for (let i = 0; i < 30; i += 1) {
    const d = new Date(start);
    d.setUTCDate(start.getUTCDate() + i);
    const key = d.toISOString().slice(0, 10);
    perDay[key] = 0;
  }
  (logs.logs || []).forEach((log) => {
    const key = log.logged_at.slice(0, 10);
    if (perDay[key] !== undefined) {
      perDay[key] += 1;
    }
  });
  const labels = Object.keys(perDay).sort();
  const values = labels.map((k) => perDay[k]);
  const ctx = document.getElementById("trend-chart").getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Daily completions",
          data: values,
          borderColor: "#0F6E56",
          backgroundColor: "rgba(15,110,86,0.1)",
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 6 } },
        y: { beginAtZero: true, precision: 0 },
      },
    },
  });
}

async function loadInsight() {
  try {
    const data = await apiFetch("/api/ai/insights");
    renderInsight(data.insight);
  } catch (e) {
    document.getElementById("insight-body").textContent =
      "No insights yet. Generate your first coach note.";
  }
}

function renderInsight(insight) {
  const body = document.getElementById("insight-body");
  if (!insight) {
    body.innerHTML = "<p>No insights yet.</p>";
    return;
  }
  body.innerHTML = `
    <div class="parts">
      <div><span class="label">Compliment</span><p>${insight.compliment || ""}</p></div>
      <div><span class="label">Observation</span><p>${insight.observation || ""}</p></div>
      <div><span class="label">Tip</span><p>${insight.tip || ""}</p></div>
    </div>`;
}

document.getElementById("refresh-insight").addEventListener("click", async () => {
  try {
    const data = await apiFetch("/api/ai/generate", "POST");
    renderInsight(data.insight);
  } catch (e) {
    alert(e.message);
  }
});

async function loadQuickLog() {
  const habits = await apiFetch("/api/habits?active_only=true");
  const container = document.getElementById("quick-log");
  container.innerHTML = "";
  (habits.habits || []).forEach((habit) => {
    const row = document.createElement("div");
    row.className = "quick-row";
    row.innerHTML = `<div><strong>${habit.name}</strong><div style="color:#6b7280;font-size:0.9rem;">${habit.category}</div></div>`;
    const btn = document.createElement("button");
    btn.className = "icon-btn";
    btn.textContent = "✓";
    btn.addEventListener("click", async () => {
      try {
        await apiFetch("/api/logs", "POST", { habit_id: habit.id, note: "" });
        btn.disabled = true;
        loadKpis();
      } catch (e) {
        alert(e.message);
      }
    });
    row.appendChild(btn);
    container.appendChild(row);
  });
}

(async () => {
  await loadKpis();
  await loadChart();
  await loadInsight();
  await loadQuickLog();
})();
