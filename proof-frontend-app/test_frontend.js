/**
 * Tests for the habit tracker's pure logic (logic.ts -> logic.js).
 * Run: node test_frontend.js
 * No browser, no DOM, no network needed — logic has no dependencies.
 */
import {
  addHabit,
  completionsThisWeek,
  createHabit,
  currentStreak,
  deleteHabit,
  filterHabits,
  isCompletedOn,
  parseHabits,
  toggleCompletion,
  updateHabit,
  weeklySummary,
} from "./logic.js";

let passed = 0;
let total = 0;

function check(name, cond) {
  total += 1;
  if (cond) {
    passed += 1;
    console.log(`PASS: ${name}`);
  } else {
    console.log(`FAIL: ${name}`);
  }
}

// Fixed "today" so streak/week maths is deterministic.
const TODAY = "2026-11-10"; // a Tuesday
const MONDAY = "2026-11-09";
const SUNDAY_BEFORE = "2026-11-08"; // previous week
const YESTERDAY = "2026-11-09";
const TWO_DAYS_AGO = "2026-11-08";
const THREE_DAYS_AGO = "2026-11-07";

function habitWith(completions, id = "h1") {
  return {
    id,
    name: "Morning workout",
    category: "Workout",
    targetPerWeek: 5,
    createdAt: "2026-11-01",
    completions: [...completions].sort(),
  };
}

/* --- create --- */
const h = createHabit("Morning workout", "Workout", 5, "h1", "2026-11-01");
check("createHabit returns a habit with empty completions", h !== null && h.completions.length === 0 && h.targetPerWeek === 5);
check("createHabit rejects an empty name", createHabit("   ", "Workout", 3) === null);
check("createHabit clamps targetPerWeek into 1..7", createHabit("X", "Health", 0)?.targetPerWeek === 1 && createHabit("X", "Health", 9)?.targetPerWeek === 7);
check("createHabit defaults a blank category to Other", createHabit("X", "  ", 3)?.category === "Other");

/* --- add / update / delete --- */
const added = addHabit([], h);
check("addHabit adds one habit without mutating the input", added.length === 1 && added[0].id === "h1");
const renamed = updateHabit(added, "h1", { name: "Evening run" });
check("updateHabit renames the habit", renamed[0].name === "Evening run" && renamed[0].id === "h1");
check("updateHabit with an unknown id leaves the list unchanged", updateHabit(added, "nope", { name: "Z" }) === added);
check("updateHabit rejects an empty new name", updateHabit(added, "h1", { name: "   " }) === added);
const deleted = deleteHabit(renamed, "h1");
check("deleteHabit removes only that habit", deleted.length === 0);
check("deleteHabit with an unknown id leaves the list unchanged", deleteHabit(added, "nope") === added);

/* --- toggle --- */
const t1 = toggleCompletion(added, "h1", TODAY);
check("toggleCompletion adds the date", isCompletedOn(t1[0], TODAY) === true);
const t2 = toggleCompletion(t1, "h1", TODAY);
check("toggleCompletion again removes the date", isCompletedOn(t2[0], TODAY) === false);
check("toggleCompletion rejects an invalid date", toggleCompletion(added, "h1", "2026-02-30") === added);
check("toggleCompletion with an unknown id leaves the list unchanged", toggleCompletion(added, "nope", TODAY) === added);

/* --- streak --- */
check("streak is 4 for four consecutive days ending today",
  currentStreak(habitWith([THREE_DAYS_AGO, TWO_DAYS_AGO, YESTERDAY, TODAY]), TODAY) === 4);
check("streak counts from yesterday when today is not done yet",
  currentStreak(habitWith([TWO_DAYS_AGO, YESTERDAY]), TODAY) === 2);
check("streak is 1 when only today is done (gap before it)",
  currentStreak(habitWith([THREE_DAYS_AGO, TODAY]), TODAY) === 1);
check("streak is 0 with no completions", currentStreak(habitWith([]), TODAY) === 0);
check("streak is 0 when the last completion was over a week ago",
  currentStreak(habitWith(["2026-11-01"]), TODAY) === 0);

/* --- weekly count --- */
check("completionsThisWeek counts only the current Mon-Sun week",
  completionsThisWeek(habitWith([SUNDAY_BEFORE, MONDAY, TODAY]), TODAY) === 2);

/* --- filter --- */
const list = [
  habitWith([], "a"),
  { ...habitWith([], "b"), name: "Read 20 pages", category: "Study" },
  { ...habitWith([], "c"), name: "Drink water", category: "Health" },
];
check("filter by query matches name case-insensitively",
  filterHabits(list, { query: "READ" }).length === 1 && filterHabits(list, { query: "READ" })[0].id === "b");
check("filter by query also matches category",
  filterHabits(list, { query: "health" }).length === 1);
check("filter by category keeps only that category",
  filterHabits(list, { category: "Workout" }).length === 1);
check("empty query + all categories returns everything",
  filterHabits(list, { query: "", category: "all" }).length === 3);
check("query with no match returns an empty list",
  filterHabits(list, { query: "zzz" }).length === 0);

/* --- summary --- */
const summaryList = [
  { ...habitWith([YESTERDAY, TODAY], "a"), targetPerWeek: 5 },
  { ...habitWith([TODAY], "b"), name: "Read", category: "Study" },
];
const s = weeklySummary(summaryList, TODAY);
check("weeklySummary totals habits, done-today, week count and best streak",
  s.totalHabits === 2 && s.completedToday === 2 && s.completionsThisWeek === 3 && s.bestStreak === 2);

/* --- persistence parsing --- */
check("parseHabits returns [] for malformed JSON", parseHabits("not json").length === 0);
check("parseHabits returns [] for wrong-shaped JSON", parseHabits('{"a":1}').length === 0);
check("parseHabits round-trips valid habits",
  parseHabits(JSON.stringify(summaryList)).length === 2);

console.log(`\n${passed}/${total} tests passed`);
process.exit(passed === total ? 0 : 1);
