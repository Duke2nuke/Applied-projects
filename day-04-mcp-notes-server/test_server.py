#!/usr/bin/env python3
"""End-to-end test for server.py via its stdio JSON-RPC interface.

Spawns the server as a subprocess with a temporary notes file, then
sends: initialize -> tools/list -> add_note x2 -> list_notes ->
search_notes -> an unknown tool (must error, not crash) -> ping.
Exits non-zero on the first failed assertion. No network, no API keys.
"""

import json
import subprocess
import sys
import tempfile
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def send(proc, obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, f"no response to {obj}"
    return json.loads(line)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        notes_file = os.path.join(tmp, "notes.json")
        proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py"), "--file", notes_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            init = send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
            )
            assert init["result"]["serverInfo"]["name"] == "mini-mcp-notes", init
            print("PASS initialize:", init["result"]["serverInfo"])

            tools = send(
                proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            )
            names = [t["name"] for t in tools["result"]["tools"]]
            assert names == ["add_note", "list_notes", "search_notes"], names
            print("PASS tools/list:", names)

            n1 = send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "add_note",
                        "arguments": {
                            "text": "MCP servers expose tools over JSON-RPC",
                            "tags": ["mcp"],
                        },
                    },
                },
            )
            note1 = json.loads(n1["result"]["content"][0]["text"])
            assert note1["id"] == 1, note1
            print("PASS add_note 1:", note1["text"])

            send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "add_note",
                        "arguments": {"text": "Buy milk", "tags": ["todo"]},
                    },
                },
            )
            listed = send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "list_notes", "arguments": {}},
                },
            )
            all_notes = json.loads(listed["result"]["content"][0]["text"])
            assert len(all_notes) == 2, all_notes
            print("PASS list_notes: 2 notes")

            found = send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "search_notes",
                        "arguments": {"query": "mcp"},
                    },
                },
            )
            hits = json.loads(found["result"]["content"][0]["text"])
            assert len(hits) == 1 and hits[0]["id"] == 1, hits
            print("PASS search_notes 'mcp': 1 hit")

            bad = send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "nope", "arguments": {}},
                },
            )
            assert "error" in bad, bad
            print("PASS unknown tool returns error, server stays up")

            pong = send(proc, {"jsonrpc": "2.0", "id": 8, "method": "ping"})
            assert pong["result"] == {}, pong
            print("PASS ping")

            # Persistence: the notes file on disk holds both notes.
            with open(notes_file, encoding="utf-8") as f:
                saved = json.load(f)
            assert len(saved) == 2, saved
            print("PASS notes persisted to file")
        finally:
            proc.stdin.close()
            proc.wait(timeout=10)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
