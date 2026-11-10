"""Tests for the Tasks API, using Flask's test client.

Runs against a temporary SQLite database (no file left behind).
Prints PASS/FAIL per case and a final X/Y count.
"""

import os
import tempfile

import app as app_module

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"PASS: {name}")
    else:
        FAIL += 1
        print(f"FAIL: {name} {detail}")


def main():
    global PASS, FAIL
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["TASKS_DB"] = tmp.name
    app_module.TOKENS.clear()
    client = app_module.app.test_client()

    # --- /health ---
    r = client.get("/health")
    check("GET /health returns 200 with status ok",
          r.status_code == 200 and r.get_json() == {"status": "ok"},
          f"(got {r.status_code} {r.get_json()})")

    # --- /login ---
    r = client.post("/login", json={"username": "demo", "password": "wrong"})
    check("POST /login wrong password returns 401",
          r.status_code == 401, f"(got {r.status_code})")
    r = client.post("/login", json={"username": "demo"})
    check("POST /login missing password returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/login", json={"username": "demo", "password": "demo1234"})
    token = r.get_json().get("token") if r.status_code == 200 else None
    check("POST /login correct demo credentials returns 200 + token",
          r.status_code == 200 and isinstance(token, str) and len(token) > 0,
          f"(got {r.status_code} {r.get_json()})")
    headers = {"Authorization": f"Bearer {token}"}

    # --- Auth failures on /tasks ---
    r = client.get("/tasks")
    check("GET /tasks without token returns 401",
          r.status_code == 401, f"(got {r.status_code})")
    r = client.get("/tasks", headers={"Authorization": "Bearer invalid-token"})
    check("GET /tasks with bad token returns 401",
          r.status_code == 401, f"(got {r.status_code})")
    r = client.post("/tasks", json={"title": "x"})
    check("POST /tasks without token returns 401",
          r.status_code == 401, f"(got {r.status_code})")

    # --- Validation failures ---
    r = client.post("/tasks", json={"title": ""}, headers=headers)
    check("POST /tasks empty title returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/tasks", json={"title": "   "}, headers=headers)
    check("POST /tasks whitespace-only title returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/tasks", json={}, headers=headers)
    check("POST /tasks missing title returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/tasks", json={"title": 123}, headers=headers)
    check("POST /tasks non-string title returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/tasks", json={"title": "ok", "done": "yes"}, headers=headers)
    check("POST /tasks non-boolean done returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.post("/tasks", json={"title": "ok", "description": 5}, headers=headers)
    check("POST /tasks non-string description returns 400",
          r.status_code == 400, f"(got {r.status_code})")

    # --- Create / list / get ---
    r = client.post("/tasks", json={"title": "Write tests", "description": "for the API"},
                    headers=headers)
    created = r.get_json() if r.status_code == 201 else {}
    task_id = created.get("id")
    check("POST /tasks valid body returns 201 with id, title, done=false",
          r.status_code == 201 and created.get("title") == "Write tests"
          and created.get("done") is False,
          f"(got {r.status_code} {created})")
    r = client.get("/tasks", headers=headers)
    check("GET /tasks returns list containing the created task",
          r.status_code == 200 and any(t["id"] == task_id for t in r.get_json()),
          f"(got {r.status_code} {r.get_json()})")
    r = client.get(f"/tasks/{task_id}", headers=headers)
    check("GET /tasks/<id> returns the task",
          r.status_code == 200 and r.get_json().get("title") == "Write tests",
          f"(got {r.status_code} {r.get_json()})")
    r = client.get("/tasks/999999", headers=headers)
    check("GET /tasks/<missing id> returns 404",
          r.status_code == 404, f"(got {r.status_code})")
    r = client.get(f"/tasks/{task_id}")
    check("GET /tasks/<id> without token returns 401",
          r.status_code == 401, f"(got {r.status_code})")

    # --- Update ---
    r = client.put(f"/tasks/{task_id}", json={"done": True}, headers=headers)
    check("PUT /tasks/<id> marks done=true",
          r.status_code == 200 and r.get_json().get("done") is True,
          f"(got {r.status_code} {r.get_json()})")
    r = client.put(f"/tasks/{task_id}", json={"title": ""}, headers=headers)
    check("PUT /tasks/<id> empty title returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.put(f"/tasks/{task_id}", json={"done": "yes"}, headers=headers)
    check("PUT /tasks/<id> non-boolean done returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.put("/tasks/999999", json={"title": "x"}, headers=headers)
    check("PUT /tasks/<missing id> returns 404",
          r.status_code == 404, f"(got {r.status_code})")
    r = client.put(f"/tasks/{task_id}", json={}, headers=headers)
    check("PUT /tasks/<id> empty body returns 400",
          r.status_code == 400, f"(got {r.status_code})")
    r = client.put(f"/tasks/{task_id}", json={"title": "Renamed"})
    check("PUT /tasks/<id> without token returns 401",
          r.status_code == 401, f"(got {r.status_code})")

    # --- Delete ---
    r = client.delete(f"/tasks/{task_id}")
    check("DELETE /tasks/<id> without token returns 401",
          r.status_code == 401, f"(got {r.status_code})")
    r = client.delete("/tasks/999999", headers=headers)
    check("DELETE /tasks/<missing id> returns 404",
          r.status_code == 404, f"(got {r.status_code})")
    r = client.delete(f"/tasks/{task_id}", headers=headers)
    check("DELETE /tasks/<id> returns 200",
          r.status_code == 200, f"(got {r.status_code})")
    r = client.get(f"/tasks/{task_id}", headers=headers)
    check("GET /tasks/<id> after delete returns 404",
          r.status_code == 404, f"(got {r.status_code})")
    r = client.get("/tasks", headers=headers)
    check("GET /tasks after delete returns empty list",
          r.status_code == 200 and r.get_json() == [],
          f"(got {r.status_code} {r.get_json()})")

    os.unlink(tmp.name)
    total = PASS + FAIL
    print(f"\n{PASS}/{total} tests passed")
    raise SystemExit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
