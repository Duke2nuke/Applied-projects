// Vanilla JS frontend for the tasks API. No build step, no dependencies.
// Token is kept in sessionStorage (cleared when the tab closes).

const API = "/api";
let token = sessionStorage.getItem("token") || null;

const $ = (id) => document.getElementById(id);
const errorEl = $("error");

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = !message;
}

function authHeaders() {
  return { "Content-Type": "application/json", "Authorization": "Bearer " + token };
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || ("Request failed: " + res.status));
  return data;
}

function renderTasks(tasks) {
  const list = $("task-list");
  list.innerHTML = "";
  $("empty").hidden = tasks.length > 0;
  for (const task of tasks) {
    const li = document.createElement("li");
    li.className = task.done ? "done" : "";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = task.done;
    checkbox.addEventListener("change", async () => {
      try {
        await api("/tasks/" + task.id, {
          method: "PATCH",
          headers: authHeaders(),
          body: JSON.stringify({ done: checkbox.checked }),
        });
        await loadTasks();
      } catch (e) { showError(e.message); checkbox.checked = task.done; }
    });

    const text = document.createElement("span");
    text.textContent = task.title + (task.notes ? " — " + task.notes : "");

    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      try {
        await api("/tasks/" + task.id, { method: "DELETE", headers: authHeaders() });
        await loadTasks();
      } catch (e) { showError(e.message); }
    });

    li.append(checkbox, text, del);
    list.appendChild(li);
  }
}

async function loadTasks() {
  showError("");
  try {
    renderTasks(await api("/tasks", { headers: authHeaders() }));
  } catch (e) { showError(e.message); }
}

function setLoggedIn(username) {
  $("login-section").hidden = true;
  $("app-section").hidden = false;
  $("who").textContent = username;
  loadTasks();
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");
  try {
    const data = await api("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("username").value, password: $("password").value }),
    });
    token = data.token;
    sessionStorage.setItem("token", token);
    setLoggedIn(data.username);
  } catch (err) { showError(err.message); }
});

$("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");
  try {
    await api("/tasks", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ title: $("new-title").value, notes: $("new-notes").value }),
    });
    $("new-title").value = "";
    $("new-notes").value = "";
    await loadTasks();
  } catch (err) { showError(err.message); }
});

$("logout").addEventListener("click", () => {
  token = null;
  sessionStorage.removeItem("token");
  $("app-section").hidden = true;
  $("login-section").hidden = false;
  showError("");
});

// If a token survived in this tab's session, skip the login form.
if (token) setLoggedIn("demo");
