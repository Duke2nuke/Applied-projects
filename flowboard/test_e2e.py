"""End-to-end tests for the full stack task app.

Uses Flask's test client against a throwaway SQLite file, checks that the
frontend files serve, and runs the full API flow:
login -> create -> list -> toggle -> delete, plus 401 / 400 / 404 cases.
Prints PASS/FAIL per case and a final X/Y count. Run: python test_e2e.py
"""
import os
import sys
import tempfile

# Point the app at a throwaway DB before importing it.
_fd, DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.remove(DB_PATH)
os.environ["TASK_DB"] = DB_PATH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition)))
    print(f"{'PASS' if condition else 'FAIL'}: {name}" + (f" — {detail}" if detail and not condition else ""))


def main():
    client = app.test_client()

    # 1. Health check
    r = client.get("/api/health")
    check("health endpoint returns 200", r.status_code == 200, f"got {r.status_code}")

    # 2-4. Frontend serves
    r = client.get("/")
    check("frontend index serves (200, contains Tasks)", r.status_code == 200 and b"Tasks" in r.data, f"got {r.status_code}")
    r = client.get("/static/app.js")
    check("frontend app.js serves (200, mentions /api/tasks)", r.status_code == 200 and b"/tasks" in r.data, f"got {r.status_code}")
    r = client.get("/static/styles.css")
    check("frontend styles.css serves (200)", r.status_code == 200, f"got {r.status_code}")

    # 5. Unauthenticated request is rejected
    r = client.get("/api/tasks")
    check("unauthenticated GET /api/tasks returns 401", r.status_code == 401, f"got {r.status_code}")

    # 6. Wrong password is rejected
    r = client.post("/api/login", json={"username": "demo", "password": "wrong"})
    check("login with wrong password returns 401", r.status_code == 401, f"got {r.status_code}")

    # 7. Demo login works and returns a token
    r = client.post("/api/login", json={"username": "demo", "password": "demo123"})
    token = r.get_json().get("token") if r.status_code == 200 else None
    check("login with demo credentials returns a token", r.status_code == 200 and bool(token), f"got {r.status_code}")
    headers = {"Authorization": f"Bearer {token}"}

    # 8. Create a task
    r = client.post("/api/tasks", json={"title": "Buy milk", "notes": "oat milk"}, headers=headers)
    created = r.get_json() if r.status_code == 201 else {}
    task_id = created.get("id")
    check("create task returns 201 with an id", r.status_code == 201 and task_id is not None, f"got {r.status_code}: {created}")

    # 9. Empty title is rejected
    r = client.post("/api/tasks", json={"title": "   "}, headers=headers)
    check("create task with empty title returns 400", r.status_code == 400, f"got {r.status_code}")

    # 10. List contains the created task
    r = client.get("/api/tasks", headers=headers)
    tasks = r.get_json() if r.status_code == 200 else []
    check("list contains the created task", any(t.get("id") == task_id for t in tasks), f"got {tasks}")

    # 11. Toggle done
    r = client.patch(f"/api/tasks/{task_id}", json={"done": True}, headers=headers)
    check("toggle task done returns done=true", r.status_code == 200 and r.get_json().get("done") is True, f"got {r.status_code}: {r.get_json()}")

    # 12. Toggling a missing task is 404
    r = client.patch("/api/tasks/999999", json={"done": True}, headers=headers)
    check("toggle missing task returns 404", r.status_code == 404, f"got {r.status_code}")

    # 13. Delete the task
    r = client.delete(f"/api/tasks/{task_id}", headers=headers)
    check("delete task returns 200", r.status_code == 200, f"got {r.status_code}")

    # 14. List no longer contains it
    r = client.get("/api/tasks", headers=headers)
    tasks = r.get_json() if r.status_code == 200 else []
    check("list after delete no longer contains the task", not any(t.get("id") == task_id for t in tasks), f"got {tasks}")

    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} tests passed")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
