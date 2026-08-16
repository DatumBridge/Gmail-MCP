# Gmail MCP Server

DatumBridge **tool-server** that exposes full Gmail capabilities over Streamable HTTP MCP. Sibling to `google-drive-mcp`.

**Class:** Python FastMCP tool-server (not a WS hub/relay). See [`docs/`](docs/README.md).

## Tools

| Area | Tools |
|------|--------|
| Messages | `list_messages`, `get_message`, `send_message`, `reply_message`, `forward_message`, `trash_message`, `untrash_message`, `delete_message`, `mark_message_read`, `mark_message_unread`, `modify_message_labels` |
| Threads | `list_threads`, `get_thread`, `trash_thread`, `untrash_thread`, `delete_thread`, `modify_thread_labels` |
| Drafts | `list_drafts`, `get_draft`, `create_draft`, `update_draft`, `send_draft`, `delete_draft` |
| Labels | `list_labels`, `create_label`, `update_label`, `delete_label` |
| Attachments | `download_attachment` (send/draft accept inline attachments; empty `[]` / JSON array objects are coerced server-side) |

Every tool requires **`credentials_path`** or **`credentials_json`** (OAuth token from Connect with Google / `scripts/oauth_connect.py`).

**Production (DatumBridge Studio):** prefer the platform **credential vault** — connect Gmail under Studio **Account → Integrations**. The MCP registry injects `credentials_json` on execute; do not put tokens in workflow parameter mappings. See `dtb-agent-kit` ADR-0004.

Registry id: **`mcpServer=gmail`**.

## Setup

1. Google Cloud Console → enable **Gmail API**.
2. Create OAuth 2.0 Client (Web and/or Desktop).
3. Save Web client as `credentials.json` (gitignored) or set `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`.
4. Add redirect URI: `http://localhost:8000/oauth/callback` (or `OAUTH_REDIRECT_URI`).
5. Consent scopes use `https://www.googleapis.com/auth/gmail.modify`.

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_mcp.txt
./mcp_server_entrypoint.sh
# or: uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- MCP: `POST http://localhost:8000/mcp/`
- Test UI: `http://localhost:8000/test` (requires `GMAIL_ENABLE_OAUTH_UI=1`)
- OAuth: `http://localhost:8000/oauth/start`

Requires **Python 3.10+** for FastMCP (Docker image uses 3.11). Helper tests run without FastMCP:

```bash
python scripts/test_helpers.py -v
```

CLI token:

```bash
python scripts/oauth_connect.py   # writes token.json
```

## Docker

```bash
docker build -t gmail-mcp .
docker run -p 8000:8000 \
  -e GOOGLE_OAUTH_CLIENT_ID=... \
  -e GOOGLE_OAUTH_CLIENT_SECRET=... \
  -e OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback \
  gmail-mcp
```

## Architecture

```text
Studio / LangGraph → POST /mcp → mcp_server tools → GmailService → Gmail API
```

- Fail-fast on missing credentials (`CREDENTIALS_REQUIRED`)
- Domain errors return structured `{error_code, error_message, retryable, ...}`
- Tools return data only (no approve/refuse/policy decisions)
- Never log tokens or message bodies

## Permanent delete

`delete_message` / `delete_thread` bypass trash and typically need broader scope than `gmail.modify` (`https://mail.google.com/`). Prefer trash tools. See [ADR-0002](docs/adr/ADR-0002-gmail-oauth-scopes.md).

## Tests

```bash
python scripts/test_helpers.py -v
```

## Project structure

```text
gmail-mcp/
├── app/mcp_server.py
├── app/oauth_routes.py
├── app/services/gmail_service.py
├── app/core/exceptions.py
├── app/schemas/mcp_models.py
├── scripts/
├── static/test-ui.html
├── docs/
├── Dockerfile
└── requirements_mcp.txt
```
