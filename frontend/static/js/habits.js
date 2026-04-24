/* static/js/habits.js */
if (!localStorage.getItem("access_token")) {
  window.location.href = mindtrackAppPath("login");
}

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

const drawer = document.getElementById("drawer");
const overlay = document.getElementById("drawer-overlay");
const fab = document.getElementById("fab");
const closeDrawer = document.getElementById("close-drawer");
const habitList = document.getElementById("habit-list");
const form = document.getElementById("habit-form");
const title = document.getElementById("drawer-title");
let editingId = null;

const emojiChoices = ["🎯", "🏃", "📚", "💧", "🧘", "💤", "🌿", "⭐"];
const emojiGrid = document.getElementById("emoji-grid");
emojiChoices.forEach((emo) => {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "emoji-option";
  btn.textContent = emo;
  btn.addEventListener("click", () => {
    document.getElementById("habit-icon").value = emo;
    emojiGrid.querySelectorAll(".emoji-option").forEach((b) => b.classList.remove("selected"));
    btn.classList.add("selected");
  });
  emojiGrid.appendChild(btn);
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

function showHabitToast(message) {
  const existing = document.querySelector(".habit-toast");
  if (existing) {
    existing.remove();
  }
  const t = document.createElement("div");
  t.className = "habit-toast";
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2800);
}

function todayUtcRange() {
  const today = new Date();
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const end = new Date(start);
  end.setUTCHours(23, 59, 59, 999);
  return { start, end };
}

function openDrawer(mode, habit) {
  editingId = mode === "edit" ? habit.id : null;
  title.textContent = mode === "edit" ? "Edit habit" : "New habit";
  form.reset();
  document.getElementById("habit-icon").value = emojiChoices[0];
  if (habit) {
    document.getElementById("habit-name").value = habit.name;
    document.getElementById("habit-description").value = habit.description || "";
    document.getElementById("habit-frequency").value = habit.frequency;
    document.getElementById("habit-category").value = habit.category;
    document.getElementById("habit-color").value = habit.color || "#0F6E56";
    document.getElementById("habit-icon").value = habit.icon || emojiChoices[0];
  }
  drawer.classList.add("open");
  overlay.classList.add("show");
}

function closePanel() {
  drawer.classList.remove("open");
  overlay.classList.remove("show");
}

fab.addEventListener("click", () => openDrawer("create"));
overlay.addEventListener("click", closePanel);
closeDrawer.addEventListener("click", closePanel);

async function loadHabits() {
  const data = await apiFetch("/api/habits");
  const { start, end } = todayUtcRange();
  let counts = {};
  try {
    const logsRes = await apiFetch(
      `/api/logs?from=${start.toISOString()}&to=${end.toISOString()}`
    );
    (logsRes.logs || []).forEach((l) => {
      counts[l.habit_id] = (counts[l.habit_id] || 0) + 1;
    });
  } catch (e) {
    counts = {};
  }

  habitList.innerHTML = "";
  (data.habits || []).forEach((habit) => {
    const card = document.createElement("div");
    card.className = "habit-card";
    const todayN = counts[habit.id] || 0;
    const icon = habit.icon || "🎯";
    card.innerHTML = `
      <div class="swatch" style="background:${escapeHtml(habit.color)};"></div>
      <div class="habit-card-head">
        <span class="habit-card-icon" aria-hidden="true">${escapeHtml(icon)}</span>
        <div class="habit-card-head-text">
          <div class="habit-card-title-row">
            <h3>${escapeHtml(habit.name)}</h3>
            <span class="badge">${escapeHtml(habit.category || "")}</span>
          </div>
          <p class="habit-desc">${escapeHtml(habit.description || "")}</p>
        </div>
      </div>
      <div class="habit-stats">
        <span>Streak <strong data-streak="${habit.id}">…</strong> days</span>
        <span>Today <strong data-today="${habit.id}">${todayN}</strong>×</span>
      </div>
      <div class="actions">
        <button type="button" class="btn-mark-done" data-done="${habit.id}">Mark complete</button>
        <button class="btn-ghost" data-edit="${habit.id}">Edit</button>
        <button class="btn-ghost" data-delete="${habit.id}">Delete</button>
      </div>`;
    habitList.appendChild(card);
    apiFetch(`/api/logs/streak/${habit.id}`)
      .then((s) => {
        const el = card.querySelector(`[data-streak="${habit.id}"]`);
        if (el) {
          el.textContent = s.streak;
        }
      })
      .catch(() => {});

    card.querySelector(`[data-done="${habit.id}"]`).addEventListener("click", async (ev) => {
      const b = ev.currentTarget;
      b.disabled = true;
      try {
        await apiFetch("/api/logs", "POST", { habit_id: habit.id, note: "" });
        const todayEl = card.querySelector(`[data-today="${habit.id}"]`);
        if (todayEl) {
          const n = parseInt(todayEl.textContent, 10) || 0;
          todayEl.textContent = String(n + 1);
        }
        const streakData = await apiFetch(`/api/logs/streak/${habit.id}`);
        const streakEl = card.querySelector(`[data-streak="${habit.id}"]`);
        if (streakEl) {
          streakEl.textContent = streakData.streak;
        }
        showHabitToast(`${habit.name} logged`);
      } catch (e) {
        showHabitToast(e && e.message ? e.message : "Could not log");
      } finally {
        b.disabled = false;
      }
    });

    card.querySelector(`[data-edit="${habit.id}"]`).addEventListener("click", () => {
      openDrawer("edit", habit);
    });
    card.querySelector(`[data-delete="${habit.id}"]`).addEventListener("click", async () => {
      if (!confirm("Delete this habit?")) {
        return;
      }
      await apiFetch(`/api/habits/${habit.id}`, "DELETE");
      loadHabits();
    });
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("habit-name").value,
    description: document.getElementById("habit-description").value,
    frequency: document.getElementById("habit-frequency").value,
    category: document.getElementById("habit-category").value,
    color: document.getElementById("habit-color").value,
    icon: document.getElementById("habit-icon").value,
  };
  if (editingId) {
    await apiFetch(`/api/habits/${editingId}`, "PUT", payload);
  } else {
    await apiFetch("/api/habits", "POST", payload);
  }
  closePanel();
  loadHabits();
});

loadHabits();
