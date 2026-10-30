#!/usr/bin/env python3
"""Minimal MCP-style notes server over stdio (standard library only).

Protocol: newline-delimited JSON-RPC 2.0, as used by MCP stdio servers.
Each line on stdin is one JSON-RPC request/notification; each response
is one JSON line on stdout. No external dependencies, no network, no API keys.

Supported methods:
  initialize                -> protocol version + capabilities + server info
  notifications/initialized -> notification, no response
  ping                      -> {}
  tools/list                -> the three tools below
  tools/call                -> add_note / list_notes / search_notes

Notes are stored as JSON in the file given by --file, the
MCP_NOTES_FILE environment variable, or ./notes.json by default.

This is a small, honest implementation of the MCP *transport + tool*
shape for learning and local testing. It was tested with the included
test_server.py harness only; it has NOT been verified against
Claude Desktop, Cursor, or any other MCP client.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "mini-mcp-notes"
SERVER_VERSION = "0.1.0"

TOOLS = [
    {
        "name": "add_note",
        "description": "Save a short note with optional tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text"],
        },
    },
    {
        "name": "list_notes",
        "description": "List all saved notes, oldest first.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_notes",
        "description": "Search notes by substring (case-insensitive) in text or tags.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


class NotesStore:
    def __init__(self, path):
        self.path = path
        self.notes = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, indent=2)

    def add(self, text, tags):
        note = {
            "id": (self.notes[-1]["id"] + 1) if self.notes else 1,
            "text": text,
            "tags": list(tags or []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.notes.append(note)
        self._save()
        return note

    def search(self, query):
        q = (query or "").lower()
        if not q:
            return list(self.notes)
        return [
            n
            for n in self.notes
            if q in n["text"].lower()
            or any(q in t.lower() for t in n["tags"])
        ]


def tool_result(payload):
    """Wrap a payload as an MCP-style tool result (text content)."""
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def handle(request, store):
    """Return a JSON-RPC response dict, or None for notifications."""
    method = request.get("method")
    req_id = request.get("id")

    # Notifications have no id and get no response.
    if req_id is None:
        return None

    params = request.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "add_note":
            text = args.get("text")
            if not isinstance(text, str) or not text.strip():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "add_note requires a non-empty 'text' string",
                    },
                }
            note = store.add(text.strip(), args.get("tags") or [])
            return {"jsonrpc": "2.0", "id": req_id, "result": tool_result(note)}
        if name == "list_notes":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result(store.notes),
            }
        if name == "search_notes":
            query = args.get("query")
            if not isinstance(query, str):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "search_notes requires a 'query' string",
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result(store.search(query)),
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"unknown tool: {name}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main():
    parser = argparse.ArgumentParser(description="Mini MCP notes server (stdio)")
    parser.add_argument(
        "--file",
        default=os.environ.get("MCP_NOTES_FILE", "notes.json"),
        help="JSON file used to store notes (default: notes.json)",
    )
    args = parser.parse_args()
    store = NotesStore(args.file)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "parse error"},
                    }
                ),
                flush=True,
            )
            continue
        if not isinstance(request, dict) or "method" not in request:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if isinstance(request, dict) else None,
                        "error": {"code": -32600, "message": "invalid request"},
                    }
                ),
                flush=True,
            )
            continue
        response = handle(request, store)
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
