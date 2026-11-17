#!/usr/bin/env python3
"""Tests for the Day 22 MCP Iris server.

Drives server.py as a subprocess over stdio and checks the full MCP
handshake, tool listing, predictions on one known flower per species,
batch predictions, the model card, and error handling for bad input
and unknown tools. Run:  python3 test_server.py
"""

import json
import subprocess
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])


class MCPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, cwd=__file__.rsplit("/", 1)[0])
        cls._next_id = 1

    @classmethod
    def tearDownClass(cls):
        cls.proc.stdin.close()
        cls.proc.wait(timeout=5)

    @classmethod
    def request(cls, method, params=None):
        rid = cls._next_id
        cls._next_id += 1
        msg = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        cls.proc.stdin.write(json.dumps(msg) + "\n")
        cls.proc.stdin.flush()
        line = cls.proc.stdout.readline()
        assert line, "server closed the connection"
        return json.loads(line)

    @classmethod
    def call_tool(cls, name, arguments):
        resp = cls.request("tools/call",
                           {"name": name, "arguments": arguments})
        assert "error" not in resp, "unexpected tool error: %s" % resp.get("error")
        return json.loads(resp["result"]["content"][0]["text"])

    def test_01_initialize(self):
        resp = self.request("initialize", {})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "mcp-iris-server")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_02_tools_list(self):
        resp = self.request("tools/list")
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, {"predict_iris", "predict_batch", "model_info"})

    def test_03_predict_setosa(self):
        out = self.call_tool("predict_iris", {"measurements": [5.1, 3.5, 1.4, 0.2]})
        self.assertEqual(out["species"], "setosa")
        self.assertAlmostEqual(sum(out["probabilities"].values()), 1.0, places=3)

    def test_04_predict_versicolor(self):
        out = self.call_tool("predict_iris", {"measurements": [6.0, 2.2, 4.0, 1.0]})
        self.assertEqual(out["species"], "versicolor")

    def test_05_predict_virginica(self):
        out = self.call_tool("predict_iris", {"measurements": [6.3, 3.3, 6.0, 2.5]})
        self.assertEqual(out["species"], "virginica")

    def test_06_predict_batch(self):
        samples = [[5.1, 3.5, 1.4, 0.2],
                   [6.0, 2.2, 4.0, 1.0],
                   [6.3, 3.3, 6.0, 2.5]]
        out = self.call_tool("predict_batch", {"samples": samples})
        self.assertEqual(out["count"], 3)
        self.assertEqual([p["species"] for p in out["predictions"]],
                         ["setosa", "versicolor", "virginica"])

    def test_07_model_info(self):
        info = self.call_tool("model_info", {})
        self.assertEqual(info["train_size"], 120)
        self.assertEqual(info["test_size"], 30)
        self.assertGreaterEqual(info["test_accuracy"], 0.9)
        self.assertEqual(info["classes"], ["setosa", "versicolor", "virginica"])

    def test_08_bad_input_is_error(self):
        resp = self.request("tools/call", {"name": "predict_iris",
                                           "arguments": {"measurements": [5.1, 3.5]}})
        self.assertIn("error", resp)
        resp = self.request("tools/call", {"name": "predict_iris",
                                           "arguments": {"measurements": ["a", 3.5, 1.4, 0.2]}})
        self.assertIn("error", resp)

    def test_09_unknown_tool_is_error(self):
        resp = self.request("tools/call", {"name": "nope", "arguments": {}})
        self.assertIn("error", resp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
