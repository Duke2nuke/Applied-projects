#!/usr/bin/env python3
"""Eval harness for the Day 22 MCP Iris server.

Drives server.py as a subprocess over stdio, sends 10 golden cases picked
deterministically from the held-out test set (the last 10 rows of each
species in data/iris.csv), and prints pass/fail plus per-call latency.

The 10 cases: test-set indices [0, 3, 7] (setosa), [10, 13, 17]
(versicolor), [20, 23, 27] (virginica), plus index 5 (setosa). Expected
labels come from the CSV itself, not from the server.

Run:  python3 eval_client.py
"""

import json
import subprocess
import sys
import time

from model import load_data, stratified_split

GOLDEN_INDICES = [0, 3, 7, 10, 13, 17, 20, 23, 27, 5]


class MCPClient:
    def __init__(self, proc):
        self.proc = proc
        self._next_id = 1

    def request(self, method, params=None):
        rid = self._next_id
        self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed the connection")
        return json.loads(line)

    def call_tool(self, name, arguments):
        t0 = time.perf_counter()
        resp = self.request("tools/call",
                            {"name": name, "arguments": arguments})
        latency_ms = (time.perf_counter() - t0) * 1000
        if "error" in resp:
            raise RuntimeError("tool error: %s" % resp["error"])
        return json.loads(resp["result"]["content"][0]["text"]), latency_ms


def main():
    _, test = stratified_split(load_data())
    cases = [(test[i][0], test[i][1]) for i in GOLDEN_INDICES]
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True, cwd=__file__.rsplit("/", 1)[0])
    try:
        client = MCPClient(proc)
        client.request("initialize", {})
        info, _ = client.call_tool("model_info", {})
        print("Model: %s | train %d (acc %.3f) | test %d (acc %.3f)"
              % (info["model"].split(" (")[0], info["train_size"],
                 info["train_accuracy"], info["test_size"],
                 info["test_accuracy"]))
        print("%-4s %-38s %-12s %-12s %-9s %s" %
              ("#", "measurements", "expected", "predicted", "correct", "latency"))
        passed = 0
        latencies = []
        for i, (x, expected) in enumerate(cases, 1):
            result, ms = client.call_tool("predict_iris", {"measurements": x})
            latencies.append(ms)
            ok = result["species"] == expected
            passed += ok
            print("%-4d %-38s %-12s %-12s %-9s %.2f ms"
                  % (i, str(x), expected, result["species"],
                     "PASS" if ok else "FAIL", ms))
        print("\n%d/10 passed | mean latency %.2f ms | max latency %.2f ms"
              % (passed, sum(latencies) / len(latencies), max(latencies)))
        return 0 if passed == len(cases) else 1
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
