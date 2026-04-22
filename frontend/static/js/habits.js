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
  habitList.innerHTML = "";
  (data.habits || []).forEach((habit) => {
    const card = document.createElement("div");
    card.className = "habit-card";
    card.innerHTML = `
      <div class="swatch" style="background:${habit.color};"></div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0;">${habit.name}</h3>
        <span class="badge">${habit.category}</span>
      </div>
      <p style="color:#6b7280;">${habit.description || ""}</p>
      <div>Current streak: <strong data-streak="${habit.id}">…</strong></div>
      <div class="actions">
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
