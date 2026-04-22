/* static/js/auth.js */
const loginTab = document.getElementById("tab-login");
const registerTab = document.getElementById("tab-register");
const loginPanel = document.getElementById("panel-login");
const registerPanel = document.getElementById("panel-register");

function activateTab(target) {
  const isLogin = target === "login";
  loginTab.classList.toggle("active", isLogin);
  registerTab.classList.toggle("active", !isLogin);
  loginPanel.classList.toggle("active", isLogin);
  registerPanel.classList.toggle("active", !isLogin);
}

loginTab.addEventListener("click", () => activateTab("login"));
registerTab.addEventListener("click", () => activateTab("register"));

function showError(id, message) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = message || "";
  }
}

function validateEmail(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("login-email-error", "");
  showError("login-password-error", "");
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  if (!email) {
    showError("login-email-error", "Email is required");
    return;
  }
  if (!validateEmail(email)) {
    showError("login-email-error", "Enter a valid email");
    return;
  }
  if (!password) {
    showError("login-password-error", "Password is required");
    return;
  }
  try {
    const data = await apiFetch("/api/auth/login", "POST", { email, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("mindtrack_user", JSON.stringify(data.user));
    const base = (window.MINDTRACK_BASE || "/").replace(/\/?$/, "/");
    window.location.href = base + "dashboard";
  } catch (err) {
    showError("login-password-error", err.message);
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  ["reg-name-error", "reg-email-error", "reg-pass-error", "reg-confirm-error"].forEach(
    (id) => showError(id, "")
  );
  const fullName = document.getElementById("register-name").value.trim();
  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;
  const confirm = document.getElementById("register-confirm").value;
  let valid = true;
  if (!fullName) {
    showError("reg-name-error", "Full name is required");
    valid = false;
  }
  if (!email) {
    showError("reg-email-error", "Email is required");
    valid = false;
  } else if (!validateEmail(email)) {
    showError("reg-email-error", "Enter a valid email");
    valid = false;
  }
  if (!password) {
    showError("reg-pass-error", "Password is required");
    valid = false;
  } else if (password.length < 8) {
    showError("reg-pass-error", "Password must be at least 8 characters");
    valid = false;
  }
  if (password !== confirm) {
    showError("reg-confirm-error", "Passwords must match");
    valid = false;
  }
  if (!valid) {
    return;
  }
  try {
    const data = await apiFetch("/api/auth/register", "POST", {
      full_name: fullName,
      email,
      password,
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("mindtrack_user", JSON.stringify(data.user));
    const base = (window.MINDTRACK_BASE || "/").replace(/\/?$/, "/");
    window.location.href = base + "dashboard";
  } catch (err) {
    showError("reg-email-error", err.message);
  }
});
