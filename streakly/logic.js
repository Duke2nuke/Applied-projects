/**
 * Habit / workout tracker — pure logic module.
 *
 * No DOM, no localStorage, no network here, so Node can test this file
 * directly (after `npm run build`) without a browser. The browser UI in app.ts
 * is a thin layer over these functions and owns all persistence.
 *
 * Dates are plain "YYYY-MM-DD" strings in the user's local timezone.
 */
export const CATEGORIES = ["Workout", "Health", "Study", "Other"];
/* ------------------------------------------------------------------ */
/* Date helpers (pure)                                                 */
/* ------------------------------------------------------------------ */
/** Format a Date as local "YYYY-MM-DD" (no UTC shift). */
export function dateISO(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}
/** "YYYY-MM-DD" for today in local time. */
export function todayISO() {
    return dateISO(new Date());
}
/** True only for a real calendar date in "YYYY-MM-DD" form. */
export function isValidDateString(s) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s))
        return false;
    const [y, m, d] = s.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}
/** "YYYY-MM-DD" shifted by n days from the given date string. */
export function addDaysISO(dateStr, n) {
    const [y, m, d] = dateStr.split("-").map(Number);
    const dt = new Date(y, m - 1, d + n);
    return dateISO(dt);
}
/** Monday ("YYYY-MM-DD") of the week containing the given date. */
export function mondayOfWeek(dateStr) {
    const [y, m, d] = dateStr.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    // JS: Sunday = 0. Monday-start: shift back (day + 6) % 7 days.
    const shift = (dt.getDay() + 6) % 7;
    return dateISO(new Date(y, m - 1, d - shift));
}
/* ------------------------------------------------------------------ */
/* CRUD                                                                */
/* ------------------------------------------------------------------ */
function makeId() {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
        return crypto.randomUUID();
    }
    return `habit-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}
function clampTarget(n) {
    if (!Number.isFinite(n))
        return 3;
    return Math.min(7, Math.max(1, Math.round(n)));
}
function normaliseCategory(c) {
    const t = c.trim();
    return t === "" ? "Other" : t.slice(0, 30);
}
/**
 * Build a new habit, or null when the name is empty / too long.
 * `id` and `createdAt` are injectable so tests can be deterministic.
 */
export function createHabit(name, category, targetPerWeek, id = makeId(), createdAt = todayISO()) {
    const cleanName = name.trim().slice(0, 80);
    if (cleanName === "")
        return null;
    if (!isValidDateString(createdAt))
        return null;
    return {
        id,
        name: cleanName,
        category: normaliseCategory(category),
        targetPerWeek: clampTarget(targetPerWeek),
        createdAt,
        completions: [],
    };
}
/** Add a habit; returns a new array, input untouched. */
export function addHabit(habits, habit) {
    return [...habits, habit];
}
/**
 * Edit a habit by id. Unknown id, or an invalid new name, leaves the
 * list unchanged (returns the same array reference).
 */
export function updateHabit(habits, id, patch) {
    const idx = habits.findIndex((h) => h.id === id);
    if (idx === -1)
        return habits;
    const old = habits[idx];
    let name = old.name;
    if (patch.name !== undefined) {
        const clean = patch.name.trim().slice(0, 80);
        if (clean === "")
            return habits;
        name = clean;
    }
    const next = {
        ...old,
        name,
        category: patch.category === undefined ? old.category : normaliseCategory(patch.category),
        targetPerWeek: patch.targetPerWeek === undefined ? old.targetPerWeek : clampTarget(patch.targetPerWeek),
    };
    return [...habits.slice(0, idx), next, ...habits.slice(idx + 1)];
}
/** Remove a habit by id; unknown id leaves the list unchanged. */
export function deleteHabit(habits, id) {
    if (!habits.some((h) => h.id === id))
        return habits;
    return habits.filter((h) => h.id !== id);
}
/* ------------------------------------------------------------------ */
/* Completions                                                         */
/* ------------------------------------------------------------------ */
export function isCompletedOn(habit, dateStr) {
    return habit.completions.includes(dateStr);
}
/**
 * Toggle a completion for one date: add it if absent, remove it if
 * present. Invalid dates and unknown ids leave the list unchanged.
 * Completions stay sorted ascending.
 */
export function toggleCompletion(habits, id, dateStr) {
    if (!isValidDateString(dateStr))
        return habits;
    const idx = habits.findIndex((h) => h.id === id);
    if (idx === -1)
        return habits;
    const old = habits[idx];
    const has = old.completions.includes(dateStr);
    const completions = has
        ? old.completions.filter((d) => d !== dateStr)
        : [...old.completions, dateStr].sort();
    const next = { ...old, completions };
    return [...habits.slice(0, idx), next, ...habits.slice(idx + 1)];
}
/* ------------------------------------------------------------------ */
/* Progress                                                            */
/* ------------------------------------------------------------------ */
/**
 * Current streak: consecutive completed days counting back from today.
 * If today is not done yet, counting starts from yesterday, so a streak
 * is not broken just because today hasn't been ticked off yet. 0 when
 * neither today nor yesterday is completed.
 */
export function currentStreak(habit, today) {
    if (!isValidDateString(today))
        return 0;
    const done = new Set(habit.completions);
    let cursor = today;
    if (!done.has(cursor))
        cursor = addDaysISO(cursor, -1);
    if (!done.has(cursor))
        return 0;
    let streak = 0;
    while (done.has(cursor)) {
        streak += 1;
        cursor = addDaysISO(cursor, -1);
    }
    return streak;
}
/** Completions in the Monday-Sunday week containing `today`. */
export function completionsThisWeek(habit, today) {
    if (!isValidDateString(today))
        return 0;
    const monday = mondayOfWeek(today);
    const sunday = addDaysISO(monday, 6);
    return habit.completions.filter((d) => d >= monday && d <= sunday).length;
}
export function weeklySummary(habits, today) {
    let completedToday = 0;
    let completionsThisWeekTotal = 0;
    let bestStreak = 0;
    for (const h of habits) {
        if (isCompletedOn(h, today))
            completedToday += 1;
        completionsThisWeekTotal += completionsThisWeek(h, today);
        bestStreak = Math.max(bestStreak, currentStreak(h, today));
    }
    return { totalHabits: habits.length, completedToday, completionsThisWeek: completionsThisWeekTotal, bestStreak };
}
/** Filter by search text and/or category. Empty query + "all" returns all. */
export function filterHabits(habits, opts = {}) {
    const q = (opts.query ?? "").trim().toLowerCase();
    const cat = (opts.category ?? "all").trim();
    return habits.filter((h) => {
        if (cat !== "all" && h.category !== cat)
            return false;
        if (q === "")
            return true;
        return h.name.toLowerCase().includes(q) || h.category.toLowerCase().includes(q);
    });
}
/* ------------------------------------------------------------------ */
/* Persistence helpers (pure JSON, storage itself lives in app.ts)     */
/* ------------------------------------------------------------------ */
/** Parse stored JSON; returns [] for anything malformed or wrong-shaped. */
export function parseHabits(json) {
    try {
        const data = JSON.parse(json);
        if (!Array.isArray(data))
            return [];
        const out = [];
        for (const item of data) {
            if (typeof item !== "object" || item === null)
                continue;
            const h = item;
            if (typeof h.id !== "string" || typeof h.name !== "string")
                continue;
            if (typeof h.category !== "string" || typeof h.targetPerWeek !== "number")
                continue;
            if (typeof h.createdAt !== "string" || !Array.isArray(h.completions))
                continue;
            if (!h.completions.every((d) => typeof d === "string" && isValidDateString(d)))
                continue;
            out.push({
                id: h.id,
                name: h.name,
                category: h.category,
                targetPerWeek: clampTarget(h.targetPerWeek),
                createdAt: h.createdAt,
                completions: [...h.completions].sort(),
            });
        }
        return out;
    }
    catch {
        return [];
    }
}
