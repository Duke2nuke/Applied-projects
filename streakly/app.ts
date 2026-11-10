/**
 * Habit / workout tracker — browser UI layer.
 *
 * All habit logic lives in logic.ts (pure, unit-tested). This file only
 * wires the DOM to it and persists habits to localStorage. No network
 * calls, no backend, no third-party code.
 */
import {
  CATEGORIES,
  addHabit,
  completionsThisWeek,
  createHabit,
  currentStreak,
  deleteHabit,
  filterHabits,
  parseHabits,
  todayISO,
  toggleCompletion,
  updateHabit,
  weeklySummary,
  type Habit,
} from "./logic.js";

const STORAGE_KEY = "habit-tracker-habits-v1";

/* ------------------------------------------------------------------ */
/* State + persistence                                                 */
/* ------------------------------------------------------------------ */

let habits: Habit[] = loadHabits();

function loadHabits(): Habit[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return seedHabits();
    return parseHabits(raw);
  } catch {
    return [];
  }
}

function saveHabits(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(habits));
  } catch {
    // Storage full / private mode: the app still works for this session.
  }
}

/**
 * Sample data shown on first run only, so the summary and streaks are
 * visible immediately. Labelled as samples in the UI; "Reset demo data"
 * restores them and "Clear all" removes everything.
 */
function seedHabits(): Habit[] {
  const today = todayISO();
  const yesterday = shift(today, -1);
  const twoDaysAgo = shift(today, -2);
  const h1 = createHabit("Morning workout", "Workout", 5, "seed-workout", today);
  const h2 = createHabit("Read 20 pages", "Study", 4, "seed-reading", today);
  const out: Habit[] = [];
  if (h1) out.push({ ...h1, completions: [twoDaysAgo, yesterday, today] });
  if (h2) out.push({ ...h2, completions: [yesterday] });
  return out;
}

function shift(dateStr: string, n: number): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d + n);
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${dt.getFullYear()}-${mm}-${dd}`;
}

/* ------------------------------------------------------------------ */
/* DOM                                                                 */
/* ------------------------------------------------------------------ */

const $ = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el as T;
};

const listEl = $("habit-list") as HTMLUListElement;
const emptyEl = $("empty-state") as HTMLParagraphElement;
const formEl = $("add-form") as HTMLFormElement;
const nameInput = $("habit-name") as HTMLInputElement;
const categoryInput = $("habit-category") as HTMLSelectElement;
const targetInput = $("habit-target") as HTMLInputElement;
const searchInput = $("search") as HTMLInputElement;
const filterSelect = $("filter-category") as HTMLSelectElement;
const summaryEl = $("summary") as HTMLDivElement;

let editingId: string | null = null;

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] ?? c);
}

function render(): void {
  const today = todayISO();
  const visible = filterHabits(habits, {
    query: searchInput.value,
    category: filterSelect.value,
  });

  // Summary
  const s = weeklySummary(habits, today);
  summaryEl.innerHTML = [
    `<div class="stat"><span class="stat-num">${s.totalHabits}</span><span class="stat-label">habits</span></div>`,
    `<div class="stat"><span class="stat-num">${s.completedToday}</span><span class="stat-label">done today</span></div>`,
    `<div class="stat"><span class="stat-num">${s.completionsThisWeek}</span><span class="stat-label">done this week</span></div>`,
    `<div class="stat"><span class="stat-num">${s.bestStreak} 🔥</span><span class="stat-label">best streak (days)</span></div>`,
  ].join("");

  // List
  emptyEl.hidden = visible.length !== 0;
  listEl.innerHTML = visible
    .map((h) => {
      const doneToday = h.completions.includes(today);
      const streak = currentStreak(h, today);
      const weekCount = completionsThisWeek(h, today);
      const pct = Math.min(100, Math.round((weekCount / h.targetPerWeek) * 100));
      if (editingId === h.id) {
        return `<li class="card editing" data-id="${esc(h.id)}">
          <input class="edit-name" type="text" value="${esc(h.name)}" maxlength="80" aria-label="Habit name">
          <select class="edit-category" aria-label="Category">
            ${CATEGORIES.map((c) => `<option ${c === h.category ? "selected" : ""}>${c}</option>`).join("")}
          </select>
          <label class="edit-target">per week
            <input class="edit-target-input" type="number" min="1" max="7" value="${h.targetPerWeek}">
          </label>
          <div class="row">
            <button class="btn primary save-edit">Save</button>
            <button class="btn cancel-edit">Cancel</button>
          </div>
        </li>`;
      }
      return `<li class="card" data-id="${esc(h.id)}">
        <div class="card-top">
          <span class="habit-name">${esc(h.name)}</span>
          <span class="badge">${esc(h.category)}</span>
        </div>
        <p class="meta">🔥 ${streak}-day streak &middot; ${weekCount}/${h.targetPerWeek} this week</p>
        <div class="bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="Weekly progress for ${esc(h.name)}">
          <div class="bar-fill" style="width: ${pct}%"></div>
        </div>
        <div class="row">
          <button class="btn ${doneToday ? "done" : "primary"} toggle-done">${doneToday ? "✓ Done today" : "Mark done today"}</button>
          <button class="btn edit">Edit</button>
          <button class="btn danger delete">Delete</button>
        </div>
      </li>`;
    })
    .join("");

  // Restore focus to the edit input when re-rendering an edit row.
  if (editingId) {
    const input = listEl.querySelector<HTMLInputElement>(".edit-name");
    input?.focus();
    input?.setSelectionRange(input.value.length, input.value.length);
  }
}

/* ------------------------------------------------------------------ */
/* Events                                                              */
/* ------------------------------------------------------------------ */

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const habit = createHabit(nameInput.value, categoryInput.value, Number(targetInput.value));
  if (!habit) {
    nameInput.focus();
    return;
  }
  habits = addHabit(habits, habit);
  saveHabits();
  formEl.reset();
  targetInput.value = "3";
  render();
});

searchInput.addEventListener("input", render);
filterSelect.addEventListener("change", render);

$("reset-demo").addEventListener("click", () => {
  habits = seedHabits();
  editingId = null;
  saveHabits();
  render();
});

$("clear-all").addEventListener("click", () => {
  if (!window.confirm("Delete all habits? This only clears this browser's local data.")) return;
  habits = [];
  editingId = null;
  saveHabits();
  render();
});

listEl.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  const card = target.closest<HTMLElement>(".card");
  if (!card) return;
  const id = card.dataset.id ?? "";
  const btn = target.closest("button");
  if (!btn) return;

  if (btn.classList.contains("toggle-done")) {
    habits = toggleCompletion(habits, id, todayISO());
  } else if (btn.classList.contains("delete")) {
    if (!window.confirm("Delete this habit?")) return;
    habits = deleteHabit(habits, id);
  } else if (btn.classList.contains("edit")) {
    editingId = id;
  } else if (btn.classList.contains("cancel-edit")) {
    editingId = null;
  } else if (btn.classList.contains("save-edit")) {
    const nameEl = card.querySelector<HTMLInputElement>(".edit-name");
    const catEl = card.querySelector<HTMLSelectElement>(".edit-category");
    const tgtEl = card.querySelector<HTMLInputElement>(".edit-target-input");
    if (!nameEl || !catEl || !tgtEl) return;
    const next = updateHabit(habits, id, {
      name: nameEl.value,
      category: catEl.value,
      targetPerWeek: Number(tgtEl.value),
    });
    if (next === habits && nameEl.value.trim() === "") {
      nameEl.focus();
      return;
    }
    habits = next;
    editingId = null;
    saveHabits();
  } else {
    return;
  }
  saveHabits();
  render();
});

render();
