# Design: Gmail MCP Server

## Class

**Python FastMCP tool-server** (DatumBridge taxonomy). Not a transport/relay — do not copy `datumbridge-mcp-ws-hub` WebSocket, pairing, or correlation patterns.

## Purpose

Expose Gmail user mailbox operations as MCP tools for DatumBridge Studio / LangGraph workflows.

## Architecture

```text
Caller → Streamable HTTP /mcp → FastMCP tools → GmailService → Gmail API v1
                 ↑
         OAuth credentials per call
```

## Key decisions

1. **Pass-through OAuth** — each tool call supplies `credentials_path` or `credentials_json` (same as google-drive-mcp). No server-side encrypted token vault in v1.
2. **Scope** — default `https://www.googleapis.com/auth/gmail.modify` (read/send/drafts/labels/trash). Permanent delete may require broader consent.
3. **Focused tools** — one capability per tool; no `gmail_execute(action=…)` god-tool.
4. **Fail-fast** — missing credentials → `CREDENTIALS_REQUIRED`, not empty success lists.
5. **Data ≠ decisions** — tools return mail data; workflows decide what to do next.
6. **Attachment cap** — `GMAIL_MAX_ATTACHMENT_BYTES` (default 25 MiB).

## Non-goals (v1)

- Gmail settings / filters / vacation / push watch
- Calendar, Contacts, Drive (use sibling MCPs)
- Shared Google OAuth library package
- WS hub / edge relay patterns
- Resources / prompts

## Platform contracts

- `GET /health`
- `POST /mcp/` Streamable HTTP (`initialize` → `Mcp-Session-Id` → `tools/list` | `tools/call`)
- Registry: `mcpServer=gmail`

See ADRs under `docs/adr/`.
