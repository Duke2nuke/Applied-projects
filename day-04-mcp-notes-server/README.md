# Day 04 — Mini MCP Notes Server (Day A: trending-skill build)

A tiny Model Context Protocol (MCP) server, written with only the
Python standard library, that exposes three tools over newline-delimited
JSON-RPC 2.0 on stdio: `add_note`, `list_notes`, and `search_notes`.
Notes persist to a JSON file. No network, no API keys, no downloads.

## The trend this builds with

**MCP / AI agents.** The 29 Oct trending check (MCP, agents,
spec-driven development) still held on the morning of 30 Oct 2026:

- GitHub Trending for Oct 2026 was dominated by AI agent frameworks
  and MCP servers (StartupCorners digest, 1 Oct 2026).
- A 2026 developer-tools guide notes MCP had 10,000+ public servers
  and 97M+ monthly SDK downloads by Dec 2025 (KodeKloud, citing
  Anthropic), and that MCP is how agents connect to tools.
- The 09:00 daily trending summary for 30 Oct had not run yet at
  build time (it runs after this 08:52 job), so this uses the
  previous day's summary plus the fresh search above, as the job rules
  require. No claim is made about today's full trending summary.

This project is deliberately *not* another ML classifier: Days 1–3
were all ML/Python (prompt injection, server anomalies, resume–JD
matching). Day A is about the tooling trend itself — how an agent
actually calls a tool.

## How to run

```bash
python3 server.py --file notes.json
```

Then send one JSON object per line on stdin, for example:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "add_note",
            "arguments": {"text": "MCP servers expose tools over JSON-RPC",
                          "tags": ["mcp"]}}}
{"jsonrpc": "2.0", "id": 4, "method": "tools/call",
 "params": {"name": "search_notes", "arguments": {"query": "mcp"}}}
```

Or run the automated test, which drives the server as a subprocess
and checks every step:

```bash
python3 test_server.py
```

## Example input / output (actually run, 30 Oct 2026)

Input (piped to `server.py`):

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call",
 "params": {"name": "add_note",
            "arguments": {"text": "demo note", "tags": ["demo"]}}}
```

Output (trimmed to the key fields; `created_at` is real UTC time):

```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05",
 "capabilities": {"tools": {}},
 "serverInfo": {"name": "mini-mcp-notes", "version": "0.1.0"}}}
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text",
 "text": "{\"id\": 1, \"text\": \"demo note\", \"tags\": [\"demo\"]}"}]}}
```

Full test output:

```
PASS initialize: {'name': 'mini-mcp-notes', 'version': '0.1.0'}
PASS tools/list: ['add_note', 'list_notes', 'search_notes']
PASS add_note 1: MCP servers expose tools over JSON-RPC
PASS list_notes: 2 notes
PASS search_notes 'mcp': 1 hit
PASS unknown tool returns error, server stays up
PASS ping
PASS notes persisted to file
ALL TESTS PASSED
```

Requirements: Python 3.10+ only. `requirements.txt` is intentionally
empty — there is nothing to install.

## 2-minute interview explainer

**Problem.** AI coding agents are only useful if they can safely use
real tools — files, databases, APIs — instead of just generating text.
MCP is the open standard for that: a client discovers a server's
tools, then calls them with structured arguments. Most explanations
stop at the diagram; this project implements the working shape.

**Approach.** A single stdlib-only Python process reads one JSON-RPC
request per line on stdin and writes one JSON response per line on
stdout — the stdio transport MCP servers use. It answers `initialize`
with a protocol version and capabilities, lists its three tools with
JSON input schemas, and dispatches `tools/call` to a small notes store
(add / list / substring search, persisted as JSON). Unknown tools and
methods return proper JSON-RPC errors instead of crashing, and
notifications (requests with no `id`) get no response, as the spec
requires.

**Results.** The included test harness spawns the server, runs the
full flow — initialize, list, add two notes, list (2 notes), search
for "mcp" (1 hit), an unknown tool (clean error), ping — and checks
the notes file on disk. All 8 checks passed on 30 Oct 2026, with no
dependencies and no network.

**Limits — stated honestly.** This implements the MCP *transport and
tool-call shape*, not a certified MCP implementation: it was tested
only with the included test harness, and has NOT been verified with
Claude Desktop, Cursor, or any other real MCP client, so do not claim
that compatibility. It is single-user and local-only (no auth, no
concurrency, notes in a plain JSON file), and search is substring
matching, not ranked retrieval. The natural next steps would be
testing against a real MCP client, adding a resource (e.g. exposing
the notes file itself), and input-size limits.
